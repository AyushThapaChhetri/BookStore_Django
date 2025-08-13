from django.core.validators import MinValueValidator
from django.db import models

from src.core.models import AbstractBaseModel


# Create your models here.
class Book(AbstractBaseModel):
    # title = models.CharField(max_length=100)
    # author = models.CharField(max_length=100)
    # publisher = models.CharField(max_length=100)
    title = models.CharField(max_length=255, db_index=True)  # Increased length for longer titles; indexed for search
    author = models.CharField(max_length=255, db_index=True)  # Increased length; indexed for queries
    publisher = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    pages = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=100)

    # Store-specific fields
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                validators=[MinValueValidator(0)])  # Monetary value with precision
    stock_quantity = models.PositiveIntegerField(default=0)  # Inventory tracking; starts at 0 (out of stock)

    is_available = models.BooleanField(default=True)  # Quick toggle for store visibility (e.g., out of stock)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)  # For book cover images

    # copies = models.PositiveIntegerField(default=1)

    def __str__(self):
        # return self.title
        return f"{self.title} by {self.author}"

    class Meta:
        indexes = [models.Index(fields=['price'])]  # Index on price for sorting/filtering in store views
