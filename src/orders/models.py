from django.conf import settings
from django.db import models

from src.books.models import Book
from src.core.models import AbstractBaseModel
from src.shipping.models import DeliveryInfo


# Create your models here.
class Order(AbstractBaseModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        help_text='User who placed this order'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    order_date = models.DateTimeField(auto_now_add=True)
    shipping_address = models.ForeignKey(
        DeliveryInfo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Shipping address for the order"
    )
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def total_after_shipping_discount(self):
        # Sum of all order item totals + shipping cost
        items_total = sum(item.total_price_after_discount for item in self.items.all())
        return items_total + self.shipping_cost

    @property
    def get_total_discount(self):
        return sum(item.discount_amount for item in self.items.all())

    def __str__(self):
        return f"Order {self.uuid} by {self.user} - {self.order_date} ({self.status})"

    class Meta:
        indexes = [models.Index(fields=['order_date', 'status'])]


class OrderItem(AbstractBaseModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='order_items',
    )

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    @property
    def base_price(self):
        # Price without any discount or extras
        return self.unit_price * self.quantity

    @property
    def total_price_after_discount(self):
        # Price for this item after discount
        return (self.unit_price - self.discount_amount) * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.book.title} in Order {self.order.uuid}"

    class Meta:
        unique_together = ('order', 'book')  # Prevents duplicate books in same order
