import uuid

from django.conf import settings
from django.db import models

from src.books.models import Book
from src.core.models import AbstractBaseModel
from src.shipping.models import DeliveryInfo


# Create your models here.

class Cart(AbstractBaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        help_text="User owning the cart (one cart per user)"
    )
    shipping_address = models.ForeignKey(
        DeliveryInfo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts_shipping_address',
    )
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user}"

    @property
    def get_total_price(self):
        # Calculate total dynamically
        return sum(item.get_subtotal() for item in self.items.all())

    @property
    def get_total_discount(self):
        "Total discounts given"
        return sum(item.discount_amount for item in self.items.all())

    @property
    def total_after_discount_shipping(self):
        """Sum of all cart items after discount + shipping"""
        items_total = sum(item.total_price_after_discount for item in self.items.all())
        return items_total + self.shipping_cost


class CartItem(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.quantity} x {self.book.title} in Cart"

    def get_subtotal(self):
        return self.quantity * self.unit_price

    @property
    def total_price_after_discount(self):
        """Price after discount of a particular item"""
        return (self.unit_price - self.discount_amount) * self.quantity

    class Meta:
        unique_together = ('cart', 'book')  # No duplicates per book in cart
