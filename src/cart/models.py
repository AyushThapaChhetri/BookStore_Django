import uuid

from django.conf import settings
from django.db import models

from src.books.models import Book
from src.core.models import AbstractBaseModel


# Create your models here.

class Cart(AbstractBaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        help_text="User owning the cart (one cart per user)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user}"

    def get_total_price(self):
        # Calculate total dynamically
        return sum(item.get_subtotal() for item in self.items.all())


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

    def __str__(self):
        return f"{self.quantity} x {self.book.title} in Cart"

    def get_subtotal(self):
        return self.quantity * self.book.stock.price

    class Meta:
        unique_together = ('cart', 'book')  # No duplicates per book in cart
