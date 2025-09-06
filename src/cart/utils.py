from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum

from .models import Cart


def round_decimal(value, places='0.01'):
    """Always return a rounded Decimal with given places."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def calculate_item_discount(item):
    """Return discount amount for a CartItem."""
    price = Decimal(str(item.book.stock.price))
    discount_pct = Decimal(str(item.book.stock.discount_percentage)) / Decimal('100')
    return price * discount_pct * item.quantity


def calculate_cart_totals(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    items = cart.items.all()
    items_count = items.count()
    total_quantity = items.aggregate(Sum('quantity'))['quantity__sum'] or 0

    total_price = sum((Decimal(str(item.get_subtotal())) for item in items), start=Decimal('0.00'))
    total_discount = sum((calculate_item_discount(item) for item in items), start=Decimal('0.00'))

    total_amount_after_discount = total_price - total_discount

    return {
        "cart": cart,
        "items": items,
        "items_count": items_count,
        "total_quantity": total_quantity,
        "total_price": round_decimal(total_price),
        "total_discount": round_decimal(total_discount),
        "total_amount_after_discount": round_decimal(total_amount_after_discount),
    }
