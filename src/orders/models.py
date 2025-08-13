from django.conf import settings
from django.db import models

from src.books.models import Book
from src.core.models import AbstractBaseModel


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
        related_name='items',
    )

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of purchase

    def __str__(self):
        return f"{self.quantity} x {self.book.title} in Order {self.order.uuid}"

    class Meta:
        unique_together = ('order', 'book')  # Prevent duplicate books in same order
