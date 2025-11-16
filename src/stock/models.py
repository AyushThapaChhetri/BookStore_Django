from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, MaxLengthValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from src.books.models import Book, Publisher
from src.core.models import AbstractBaseModel
from src.core.validators.dates import validate_date, validate_past_dates
from src.core.validators.numbers import validate_minimum_stock, validate_positive_integer


# Create your models here.

class Stock(AbstractBaseModel):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name='stock')
    current_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                        validators=[MinValueValidator(0.00)])
    current_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
                                                      validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_available = models.BooleanField(default=False)
    last_restock_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Stock for {self.book.title}"

    class Meta:
        indexes = [
            models.Index(fields=['current_price']),

        ]

    @property
    def can_sell(self):
        return self.total_remaining_quantity > 0 and self.current_price > 0

    @property
    def total_remaining_quantity(self):
        if self.pk:
            return self.batches.aggregate(total=Sum('remaining_quantity'))['total'] or 0
        return 0

    @property
    def discount_amount(self):
        discount_amount = self.current_price - self.price_after_discount
        return discount_amount

    @property
    def price_after_discount(self):
        return self.current_price * (
                1 - self.current_discount_percentage / 100
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        quantity_ok = self.total_remaining_quantity > 1
        price_ok = self.current_price > 1

        new_is_available = quantity_ok and price_ok

        self.is_available = new_is_available

        super().save(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #
    #     super().save(*args, **kwargs)
    #
    #
    #     new_is_available = self.total_remaining_quantity > 0
    #     if self.is_available != new_is_available:
    #         self.is_available = new_is_available
    #
    #         super().save(update_fields=['is_available'])


class StockBatch(AbstractBaseModel):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='batches')
    received_date = models.DateField(default=timezone.now, validators=[validate_date, validate_past_dates])
    initial_quantity = models.PositiveIntegerField(validators=[validate_minimum_stock])
    remaining_quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                    validators=[MinValueValidator(0.00), validate_positive_integer])
    supplier = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True,
                                 blank=True)
    notes = models.TextField(blank=True, null=True, validators=[MaxLengthValidator(1000)])

    def __str__(self):
        return f"Batch for {self.stock.book.title} on {self.received_date} (Remaining: {self.remaining_quantity})"

    class Meta:
        ordering = ['received_date']
        indexes = [
            models.Index(fields=['stock', 'received_date']),
            models.Index(fields=['remaining_quantity']),
        ]

    def save(self, *args, **kwargs):
        if self.pk is None:  # On creation, set remaining to initial
            self.remaining_quantity = self.initial_quantity
        super().save(*args, **kwargs)


class StockHistory(AbstractBaseModel):
    CHANGE_TYPES = (
        ('restock', 'Restock'),
        ('editstock', 'Edit Stock'),
        ('reserve', 'Reserve for Order'),
        ('release_reserve', 'Release Reservation'),
        ('sold', 'Sold'),

    )

    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, related_name='stock_history')
    batch = models.ForeignKey('StockBatch', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='history')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    quantity_change = models.IntegerField()
    before_quantity = models.PositiveIntegerField(null=True, blank=True)
    after_quantity = models.PositiveIntegerField(null=True, blank=True)
    reason = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='stock_changes')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True,
                              blank=True)

    def __str__(self):
        return f"{self.change_type} for {self.stock.book.title} on {self.created_at} (Change: {self.quantity_change})"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stock', '-created_at']),
            models.Index(fields=['change_type']),
        ]


class PriceHistory(AbstractBaseModel):
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE, related_name='price_history')
    old_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    old_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    new_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='price_changes')
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Price change for {self.stock.book.title} on {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stock', '-created_at']),
        ]


class StockReservation(AbstractBaseModel):
    stock = models.ForeignKey('stock.Stock', on_delete=models.CASCADE, related_name='reservations')
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.CASCADE, related_name='reservation')
    batch = models.ForeignKey('StockBatch', on_delete=models.CASCADE, related_name='reservations')
    reserved_quantity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Reservation of {self.reserved_quantity} from batch {self.batch} for OrderItem {self.order_item}"

    class Meta:
        indexes = [
            models.Index(fields=['order_item', 'is_active']),
            models.Index(fields=['batch']),
        ]
