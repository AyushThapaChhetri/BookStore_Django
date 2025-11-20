from datetime import datetime, date
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from src.stock.models import PriceHistory, StockBatch, StockHistory, StockReservation


def compute_batch_sold_cost(batch, book):
    actual_sold_quantity = Decimal("0.00")
    sold_amount = Decimal("0.00")

    sold_histories = [h for h in batch.history.all() if h.change_type == 'sold']

    for history in sold_histories:

        actual_sold_quantity += abs(history.quantity_change)

        items = [
            item for item in history.order.items.all()
            if item.book_id == book.id
        ]

        for item in items:

            reservations = [r for r in batch.reservations.all() if r.order_item_id == item.id]
            for res in reservations:
                quantity = res.reserved_quantity
                unit_price_after_discount = item.unit_price - item.discount_amount
                line_total = unit_price_after_discount * quantity

                sold_amount += line_total

    store_cost = batch.unit_cost * actual_sold_quantity
    net_amount = sold_amount - store_cost

    return {
        "sold_cost": sold_amount,
        "net_amount": net_amount
    }


def update_stock_price(stock, new_price, new_discount, user, reason="Manual update"):
    old_price = stock.current_price
    old_discount = stock.current_discount_percentage

    stock.current_price = Decimal(new_price)
    stock.current_discount_percentage = Decimal(new_discount)
    stock.save()

    PriceHistory.objects.create(
        stock=stock,
        old_price=old_price,
        new_price=new_price,
        old_discount_percentage=old_discount,
        new_discount_percentage=new_discount,
        changed_by=user,
        reason=reason
    )


def add_stock_batch(stock, initial_quantity, unit_cost, user, received_date=None, notes=None):
    supplier = stock.book.publisher
    before_qty = stock.total_remaining_quantity

    default_note = "Restocked"
    batch = StockBatch.objects.create(
        stock=stock,
        initial_quantity=initial_quantity,
        remaining_quantity=initial_quantity,
        unit_cost=unit_cost,
        received_date=received_date,
        supplier=supplier,
        notes=notes if notes not in [None, ""] else default_note,
    )

    if received_date:
        stock.last_restock_date = received_date
    else:
        latest_batch = (
            StockBatch.objects
            .filter(stock=stock)
            .exclude(received_date=None)
            .order_by('-received_date', '-created_at')
            .first()
        )
        if latest_batch:
            stock.last_restock_date = latest_batch.received_date or batch.created_at.date()
        else:
            stock.last_restock_date = timezone.now().date()

    stock.save()

    print("Initial price before: ", before_qty)

    StockHistory.objects.create(
        stock=stock,
        batch=batch,
        change_type="restock",
        quantity_change=initial_quantity,
        before_quantity=before_qty,
        after_quantity=before_qty + initial_quantity,
        changed_by=user,
        reason="New batch added",
    )

    return batch


class StockService:
    @staticmethod
    @transaction.atomic
    def restock(stock, initial_quantity, unit_cost, user, received_date=None, notes=None):
        return add_stock_batch(stock, initial_quantity, unit_cost, user, received_date, notes)

    @staticmethod
    @transaction.atomic
    def update_price(stock, new_price, new_discount, user, reason="Manual update"):

        update_stock_price(stock, new_price, new_discount, user, reason)

    @staticmethod
    @transaction.atomic
    def edit_stockBatch(form, book, request, batch_uuid):
        batch = get_object_or_404(book.stock.batches, uuid=batch_uuid)
        stock = batch.stock
        # changed_fields = form.changed_data
        # if not changed_fields:
        # if not form.has_changed():
        #     print("no changes found")
        #     return {"updated": False, "message": "No changes detected."}

        print("Inside service function")
        changes = {}
        for field in form.cleaned_data:
            old = getattr(batch, field)
            new = form.cleaned_data[field]

            if isinstance(old, Decimal):
                old = old.quantize(Decimal("0.01"))
                new = Decimal(new).quantize(Decimal("0.01"))

            if isinstance(old, (datetime, date)) and isinstance(new, str):
                new = datetime.strptime(new, "%Y-%m-%d").date()

            if old != new:
                changes[field] = (old, new)

        if not changes:
            print("No changes")
            return {"updated": False, "message": "No changes detected."}

        print('changes', changes)

        if "initial_quantity" in changes:
            old_initial, new_initial = changes["initial_quantity"]
            print("old initial: ", old_initial)
            print("new initial: ", new_initial)

            qty_change_before = abs(new_initial - old_initial)
            print("qty_change_before: ", qty_change_before)

            # if old_initial == batch.remaining_quantity:
            if batch.initial_quantity == batch.remaining_quantity:
                quantity_change = -qty_change_before if old_initial > new_initial else qty_change_before
                print("Qty change after: ", quantity_change)

                before_qty = old_initial
                after_qty = old_initial + quantity_change

                print('qc:', quantity_change)
                print('bq:', before_qty)
                print('aq:', after_qty)

                batch.unit_cost = form.cleaned_data["unit_cost"]
                batch.notes = form.cleaned_data["notes"]
                batch.received_date = form.cleaned_data["received_date"]
                batch.remaining_quantity = new_initial
                batch.initial_quantity = new_initial
                batch.save(update_fields=[
                    "initial_quantity",
                    "remaining_quantity",
                    "unit_cost",
                    "notes",
                    "received_date",
                    "updated_at",
                ])

                StockHistory.objects.create(
                    stock=stock,
                    batch=batch,
                    change_type="editstock",
                    quantity_change=quantity_change,
                    before_quantity=before_qty,
                    after_quantity=after_qty,
                    changed_by=request.user,
                    reason="Stock Batch Manual Edit",
                )
                return {"updated": True, "message": "Batch updated with quantity correction."}
            else:
                return {"updated": False,
                        "error": f"Cannot Edit the stock because Batch is Already in Use."}
        instance = form.save(commit=False)
        instance.save(update_fields=["unit_cost", "notes", "received_date", "updated_at", ])
        return {"updated": True, "message": "Batch details updated successfully."}

    @staticmethod
    @transaction.atomic
    def reserve_for_order(order_item, changed_by=None):

        stock = order_item.book.stock
        needed = order_item.quantity
        reserved = 0

        batches = stock.batches.filter(remaining_quantity__gt=0).select_for_update().order_by('received_date',
                                                                                              'created_at')

        for batch in batches:
            if reserved >= needed:
                break
            can_reserve = min(batch.remaining_quantity, needed - reserved)
            before = batch.remaining_quantity
            batch.remaining_quantity -= can_reserve
            batch.save()

            reservation = StockReservation.objects.create(
                stock=stock,
                order_item=order_item,
                batch=batch,
                reserved_quantity=can_reserve
            )

            StockHistory.objects.create(
                stock=stock,
                batch=batch,
                change_type='reserve',
                quantity_change=-can_reserve,
                before_quantity=before,
                after_quantity=batch.remaining_quantity,
                changed_by=changed_by,
                order=order_item.order,
                reason="Order reservation"
            )

            reserved += can_reserve

        if reserved < needed:
            raise ValueError("Not enough stock")

        stock.save()
        return reserved

    @staticmethod
    @transaction.atomic
    def release_reservation(order_item, changed_by=None):

        active_reservations = order_item.reservation.filter(
            is_active=True
        ).select_related('batch', 'batch__stock')

        if not active_reservations.exists():
            return

        affected_stocks = set()

        for reservation in active_reservations:
            batch = reservation.batch
            if not batch:
                continue

            before = batch.remaining_quantity
            batch.remaining_quantity += reservation.reserved_quantity
            batch.save()

            reservation.is_active = False
            reservation.save()

            StockHistory.objects.create(
                stock=batch.stock,
                batch=batch,
                change_type='release_reserve',
                quantity_change=reservation.reserved_quantity,
                before_quantity=before,
                after_quantity=batch.remaining_quantity,
                changed_by=changed_by,
                order=order_item.order,
                reason="Reservation released due to order cancellation"
            )

            affected_stocks.add(batch.stock)

        for stock in affected_stocks:
            stock.save()

    @staticmethod
    @transaction.atomic
    def finalize_reservation(order_item, changed_by=None):
        active_reservations = order_item.reservation.filter(is_active=True).select_related('batch', 'batch__stock')

        if not active_reservations.exists():
            return

        for reservation in active_reservations:
            reservation.is_active = False
            reservation.save()

            StockHistory.objects.create(
                stock=reservation.batch.stock,
                batch=reservation.batch,
                change_type='sold',
                quantity_change=-reservation.reserved_quantity,
                before_quantity=None,
                after_quantity=None,
                changed_by=changed_by,
                order=order_item.order,
                reason="Order completed and stock finalized"
            )
