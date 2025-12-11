from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum, Value, Count, ExpressionWrapper, F, DecimalField, Prefetch, Subquery, OuterRef
from django.db.models.functions import Coalesce

from .models import Cart, CartItem
from ..stock.models import StockBatch


def round_decimal(value, places='0.01'):
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def calculate_item_discount(item):
    price = Decimal(str(item.book.stock.current_price))
    discount_pct = Decimal(str(item.book.stock.current_discount_percentage)) / Decimal('100')
    return price * discount_pct * item.quantity


def calculate_cart_totals(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    # items = cart.items.all()
    # items_count = items.count()

    annotated_items = Prefetch(
        'items',
        queryset=CartItem.objects.annotate(
            total_remaining=Subquery(
                StockBatch.objects.filter(
                    stock=OuterRef('book__stock'),
                ).values('stock')
                .annotate(total=Sum('remaining_quantity'))
                .values('total')[:1]
            )
        )
    )

    cartqs = (
        Cart.objects.filter(id=cart.id)
        .prefetch_related(annotated_items, 'items__book', 'items__book__stock', 'items__book__authors')
        .annotate(
            item_count=Coalesce(Count('items'), Value(0)),
            total_quantity=Coalesce(Sum('items__quantity'), Value(0)),
            total_price=ExpressionWrapper(
                Coalesce(Sum(F('items__quantity') * F('items__unit_price')), Value(0)),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            total_discount=ExpressionWrapper(
                Coalesce(
                    Sum(
                        F('items__quantity')
                        * F('items__book__stock__current_price')
                        * F('items__book__stock__current_discount_percentage') / 100
                    ),
                    Value(0)
                ),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).first()
    )

    print("Cartqs:", cartqs)
    # print("Cartqs tot qty:", cartqs.total_quantity)
    print('hhhhhhhh')

    items = cartqs.items.all()

    # price = Decimal(str(item.book.stock.current_price))
    # discount_pct = Decimal(str(item.book.stock.current_discount_percentage)) / Decimal('100')
    # return price * discount_pct * item.quantity

    print('item count: ', cartqs.item_count)

    # total_quantity = items.aggregate(Sum('quantity'))['quantity__sum'] or 0
    #
    # total_price = sum((Decimal(str(item.get_subtotal())) for item in items), start=Decimal('0.00'))
    # total_discount = sum((calculate_item_discount(item) for item in items), start=Decimal('0.00'))

    # total_amount_after_discount = total_price - total_discount
    total_amount_after_discount = cartqs.total_price - cartqs.total_discount
    # print("Cart hello")
    print(items)
    for item in items:
        print('items: ', item)
        print('items qty: ', item.total_remaining)
        item.cannot_purchase = item.book.is_deleted
    # print(list(item for item in items))
    # for item in items:
    #     book = item.book
    #     print(f"\nBook: {book.title}")
    #     print("Authors:", list(book.authors.values_list("name", flat=True)))

    return {
        "cart": cart,
        # "items": items,
        "items": items,
        # "items_count": items_count,
        "items_count": cartqs.item_count,
        "total_quantity": cartqs.total_quantity,
        # "total_price": round_decimal(total_price),
        "total_price": round_decimal(cartqs.total_price),
        "total_discount": round_decimal(cartqs.total_discount),
        "total_amount_after_discount": round_decimal(total_amount_after_discount),
    }
