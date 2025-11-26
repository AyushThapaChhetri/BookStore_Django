from datetime import datetime

from django.core.exceptions import ValidationError


def validate_date_range(from_date_str, to_date_str, date_format="%Y-%m-%d"):
    print("validate_date_range called with:", from_date_str, to_date_str)

    if not from_date_str and not to_date_str:
        return None, None

    errors = {}
    from_date = None
    to_date = None

    if not from_date_str:
        errors['from'] = "From date must be provided."
    else:
        try:
            print("Parsing from_date:", from_date_str)
            from_date = datetime.strptime(from_date_str, date_format).date()
        except ValueError:
            print("Failed to parse from_date")
            errors['from'] = f"'From' date is not a valid date. Expected format: {date_format}"

    if not to_date_str:
        errors['to'] = "To date must be provided."
    else:
        try:

            to_date = datetime.strptime(to_date_str, date_format).date()
        except ValueError:
            errors['to'] = f"'To' date is not a valid date. Expected format: {date_format}"

    if from_date and to_date and from_date > to_date:
        errors['from'] = "'From' date cannot be later than 'To' date."
        errors['to'] = "'To' date cannot be earlier than 'From' date."

    if errors:
        raise ValidationError(errors)

    return from_date, to_date


def verify_batch_calculation(batch_id, book_id):
    from src.stock.models import StockBatch, StockHistory, StockReservation
    from decimal import Decimal

    batch = StockBatch.objects.with_profit_loss(book_id).get(pk=batch_id)

    sold_histories = StockHistory.objects.filter(
        batch_id=batch_id,
        change_type='sold',
        stock__book_id=book_id
    )

    manual_qty = sum(abs(h.quantity_change) for h in sold_histories)

    sold_order_ids = set(h.order_id for h in sold_histories if h.order_id)

    reservations = StockReservation.objects.filter(
        batch_id=batch_id,
        order_item__book_id=book_id,
        order_item__order_id__in=sold_order_ids,
        is_active=False
    ).select_related('order_item')

    manual_revenue = Decimal('0.00')
    for res in reservations:
        unit_price = Decimal(str(res.order_item.unit_price))
        discount = Decimal(str(res.order_item.discount_amount or 0))
        manual_revenue += res.reserved_quantity * (unit_price - discount)

    manual_cost = Decimal(manual_qty) * batch.unit_cost
    manual_profit = manual_revenue - manual_cost

    all_inactive = StockReservation.objects.filter(
        batch_id=batch_id,
        order_item__book_id=book_id,
        is_active=False
    ).count()

    sold_only = len(reservations)
    cancelled = all_inactive - sold_only

    print(f"\n{'=' * 70}")
    print(f"Batch: {batch}")
    print(f"{'=' * 70}")

    print(f"\n DATABASE CALCULATION:")
    print(f"   Sold Qty:    {batch.sold_qty}")
    print(f"   Revenue:     ${batch.sold_amount}")
    print(f"   COGS:        ${batch.cost_amount}")
    print(f"   Profit/Loss: ${batch.net_amount}")

    print(f"\n MANUAL VERIFICATION:")
    print(f"   Sold Qty:    {manual_qty}")
    print(f"   Revenue:     ${manual_revenue}")
    print(f"   COGS:        ${manual_cost}")
    print(f"   Profit/Loss: ${manual_profit}")

    print(f"\ RESERVATION BREAKDOWN:")
    print(f"   Total Inactive Reservations: {all_inactive}")
    print(f"   ├─ Sold:      {sold_only} ")
    print(f"   └─ Cancelled: {cancelled} ")

    matches = (
            batch.sold_qty == manual_qty and
            abs(batch.sold_amount - manual_revenue) < Decimal('0.01')
    )

    print(f"\n{' MATCH!' if matches else ' MISMATCH!'}")
    print(f"{'=' * 70}\n")

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
        'reservations': {
            'total_inactive': all_inactive,
            'sold': sold_only,
            'cancelled': cancelled
        },
        'match': matches
    }
