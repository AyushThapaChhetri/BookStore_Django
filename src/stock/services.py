from decimal import Decimal

from django.db import transaction

from src.stock.models import PriceHistory, StockBatch, StockHistory, StockReservation


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

    batch = StockBatch.objects.create(
        stock=stock,
        initial_quantity=initial_quantity,
        remaining_quantity=initial_quantity,
        unit_cost=unit_cost,
        received_date=received_date,
        supplier=supplier,
        notes=notes,
    )

    # stock.total_quantity += initial_quantity
    stock.save()

    print("inital price before: ", before_qty)

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

    # @staticmethod
    # @transaction.atomic
    # def update_price(stock, new_price, new_discount, user, received_date=None):
    #     return update_stock_price(stock, new_price, new_discount, user, reason="Manual update")

    @staticmethod
    @transaction.atomic
    def update_price(stock, new_price, new_discount, user, reason="Manual update"):

        update_stock_price(stock, new_price, new_discount, user, reason)

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

        stock.save()  # Update is_available
        return reserved

    @staticmethod
    @transaction.atomic
    def release_reservation(order_item, changed_by=None):

        reservation = getattr(order_item, 'reservation', None)
        if not reservation or not reservation.is_active:
            return

        batch = reservation.batch
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
            reason="Reservation released"
        )

        batch.stock.save()

    @staticmethod
    @transaction.atomic
    def finalize_reservation(order_item, changed_by=None):
        """
        Finalize reservation when order is completed (delivered/paid).
        - Keeps reservation inactive (fulfilled).
        - Logs it as 'sold'.
        """
        reservation = getattr(order_item, 'reservation', None)
        if not reservation or not reservation.is_active:
            return

        reservation.is_active = False
        reservation.save()

        StockHistory.objects.create(
            stock=reservation.batch.stock,
            batch=reservation.batch,
            change_type='sold',
            quantity_change=-reservation.reserved_quantity,
            before_quantity=None,  # Optional
            after_quantity=None,
            changed_by=changed_by,
            order=order_item.order,
            reason="Order completed and stock finalized"
        )
