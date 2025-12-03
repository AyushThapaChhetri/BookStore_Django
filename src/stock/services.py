from datetime import datetime, date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, DecimalField, Q, F
from django.db.models.functions import Coalesce, Abs
from django.shortcuts import get_object_or_404
from django.utils import timezone

from src.stock.models import PriceHistory, StockBatch, StockHistory, StockReservation


def verify_batch_calculation(batch_id, book_id):
    from src.stock.models import StockBatch, StockReservation
    from decimal import Decimal

    batch = StockBatch.objects.with_profit_loss(book_id).get(pk=batch_id)

    reservations = StockReservation.objects.filter(
        batch_id=batch_id,
        order_item__book_id=book_id,
        is_active=False
    ).select_related('order_item')

    manual_qty = 0
    manual_revenue = Decimal('0.00')

    for res in reservations:
        manual_qty += res.reserved_quantity
        unit_price = Decimal(str(res.order_item.unit_price))
        discount = Decimal(str(res.order_item.discount_amount or 0))
        manual_revenue += res.reserved_quantity * (unit_price - discount)

    manual_cost = Decimal(manual_qty) * batch.unit_cost
    manual_profit = manual_revenue - manual_cost

    print(f"\n{'=' * 60}")
    print(f"Batch: {batch}")
    print(f"{'=' * 60}")

    print(f"Sold Qty: {batch.sold_qty}")
    print(f"Revenue: ${batch.sold_amount}")
    print(f"COGS: ${batch.cost_amount}")
    print(f"Profit/Loss: ${batch.net_amount}")

    print(f"MANUAL VERIFICATION:")
    print(f"Sold Qty: {manual_qty}")
    print(f"Revenue: ${manual_revenue}")
    print(f"COGS: ${manual_cost}")
    print(f"Profit/Loss: ${manual_profit}")

    print(f"\n MATCH: {batch.sold_qty == manual_qty and batch.sold_amount == manual_revenue}")
    print(f"{'=' * 60}\n")

    return {
        'db': {
            'qty': batch.sold_qty,
            'revenue': batch.sold_amount,
            'cost': batch.cost_amount,
            'profit': batch.net_amount
        },
        'manual': {
            'qty': manual_qty,
            'revenue': manual_revenue,
            'cost': manual_cost,
            'profit': manual_profit
        },
        'match': batch.sold_qty == manual_qty and batch.sold_amount == manual_revenue
    }


def calculate_revenue_cost(stock, period_start=None, period_end=None):
    filters = {}
    if period_start:
        filters['created_at__gte'] = period_start
    if period_end:
        filters['created_at__lte'] = period_end

    orders = StockHistory.objects.filter(
        stock=stock,
        change_type='sold',
        order__isnull=False,
        **filters
    ).values_list('order_id', flat=True).distinct()

    total_revenue = Decimal('0.00')
    total_cost = Decimal('0.00')

    if orders:
        reservations = StockReservation.objects.filter(
            stock=stock,
            order_item__order_id__in=list(orders),
            is_active=False
        ).select_related('batch', 'order_item')

        for r in reservations:
            unit_revenue = r.order_item.unit_price - (r.order_item.discount_amount or Decimal('0.00'))
            revenue = unit_revenue * Decimal(r.reserved_quantity)
            cost = r.batch.unit_cost * Decimal(r.reserved_quantity)
            total_revenue += revenue
            total_cost += cost

    return total_revenue, total_cost


def _calculate_opening_closing_stock(stock, period_start, period_end, has_date_filter=False):
    from src.stock.models import StockHistory

    DECIMAL = DecimalField(max_digits=14, decimal_places=2)

    if not has_date_filter:
        all_transactions = StockHistory.objects.filter(
            stock=stock
        ).aggregate(
            sold_qty=Coalesce(
                Sum(Abs(F('quantity_change')), filter=Q(change_type='sold')),
                0
            ),
            restock_qty=Coalesce(
                Sum('quantity_change', filter=Q(change_type='restock')),
                0
            ),
            adjustment_qty=Coalesce(
                Sum('quantity_change', filter=Q(change_type='editstock')),
                0
            ),
            reserve_qty=Coalesce(
                Sum('quantity_change', filter=Q(change_type='reserve')),
                0
            ),
            release_qty=Coalesce(
                Sum('quantity_change', filter=Q(change_type='release_reserve')),
                0
            ),
        )

        closing_quantity = (
                all_transactions['restock_qty'] +
                all_transactions['adjustment_qty'] +
                all_transactions['reserve_qty'] +
                all_transactions['release_qty']
        )

        total_revenue, total_cost = calculate_revenue_cost(stock)

        closing_value = total_revenue - total_cost

        order_process = abs(all_transactions['reserve_qty']) - all_transactions['release_qty'] - abs(
            all_transactions['sold_qty'])
        restock_with_adjustment = all_transactions['restock_qty'] - abs(all_transactions['adjustment_qty'])

        return {
            'opening_quantity': 0,
            'opening_value': Decimal('0.00'),
            'closing_quantity': closing_quantity,
            'closing_value': closing_value,
            'period_profit': closing_value,
            'order_process': order_process,
            'sold_quantity': abs(all_transactions['sold_qty']),
            'restock_today': all_transactions['restock_qty'],
            'restock_with_adjustment': restock_with_adjustment,
            'adjustment_today': all_transactions['adjustment_qty'],
            'reserve_today': all_transactions['reserve_qty'],
            'release_today': all_transactions['release_qty'],
            'total_actual_sold_cost': total_revenue,  # Add these
            'total_actual_cost_cost': total_cost,  # Add these
        }

    opening_transactions = StockHistory.objects.filter(
        stock=stock,
        created_at__lt=period_start
    ).aggregate(
        restock_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='restock')),
            0
        ),
        adjustment_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='editstock')),
            0
        ),
        reserve_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='reserve')),
            0
        ),
        release_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='release_reserve')),
            0
        ),
        sold_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='sold')),
            0
        ),
    )

    opening_quantity = (
            opening_transactions['restock_qty'] +
            opening_transactions['adjustment_qty'] +
            opening_transactions['reserve_qty'] +
            opening_transactions['release_qty']
    )

    opening_revenue, opening_cost = calculate_revenue_cost(stock, period_end=period_start)
    opening_value = opening_revenue - opening_cost

    # Period transactions
    period_transactions = StockHistory.objects.filter(
        stock=stock,
        created_at__gte=period_start,
        created_at__lte=period_end
    ).aggregate(
        sold_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='sold')),
            0
        ),
        restock_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='restock')),
            0
        ),
        adjustment_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='editstock')),
            0
        ),
        reserve_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='reserve')),
            0
        ),
        release_qty=Coalesce(
            Sum('quantity_change', filter=Q(change_type='release_reserve')),
            0
        ),
    )

    period_movements = (
            period_transactions['restock_qty'] +
            period_transactions['adjustment_qty'] +
            period_transactions['reserve_qty'] +
            period_transactions['release_qty']
    )

    closing_quantity = opening_quantity + period_movements

    closing_revenue, closing_cost = calculate_revenue_cost(stock, period_end=period_end)

    closing_value = closing_revenue - closing_cost

    period_revenue, period_cost = calculate_revenue_cost(stock, period_start=period_start, period_end=period_end)

    order_process = abs(period_transactions['reserve_qty']) - period_transactions['release_qty'] - abs(
        period_transactions['sold_qty'])
    restock_with_adjustment = period_transactions['restock_qty'] - abs(period_transactions['adjustment_qty'])
    stock_not_placed = restock_with_adjustment - abs(period_transactions['reserve_qty'])

    return {
        'opening_quantity': opening_quantity,
        'opening_value': opening_value,
        'closing_quantity': closing_quantity,
        'closing_value': closing_value,
        'period_profit': closing_value - opening_value,
        'order_process': order_process,
        'stock_not_placed': max(stock_not_placed, 0),
        'sold_quantity': abs(period_transactions['sold_qty']),
        'restock_today': period_transactions['restock_qty'],
        'restock_with_adjustment': restock_with_adjustment,
        'adjustment_today': period_transactions['adjustment_qty'],
        'reserve_today': abs(period_transactions['reserve_qty']),
        'release_today': period_transactions['release_qty'],
        'total_actual_sold_cost': period_revenue,
        'total_actual_cost_cost': period_cost,
    }


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
