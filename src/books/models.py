# Create your models here.
# class Book(AbstractBaseModel):
#     title = models.CharField(max_length=255, db_index=True)  # Increased length for longer titles; indexed for search
#     author = models.CharField(max_length=255, db_index=True)  # Increased length; indexed for queries
#     publisher = models.CharField(max_length=255)
#     description = models.TextField(blank=True, null=True)
#     pages = models.PositiveIntegerField(null=True, blank=True)
#     language = models.CharField(max_length=100)
#
#     # Store-specific fields
#     price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
#                                 validators=[MinValueValidator(0)])  # Monetary value with precision
#     stock_quantity = models.PositiveIntegerField(default=0)  # Inventory tracking; starts at 0 (out of stock)
#
#     is_available = models.BooleanField(default=True)  # Quick toggle for store visibility (e.g., out of stock)
#     cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)  # For book cover images
#
#     def __str__(self):
#         # return self.title
#         return f"{self.title} by {self.author}"
#
#     class Meta:
#         indexes = [models.Index(fields=['price'])]  # Index on price for sorting/filtering in store views
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from src.core.models import AbstractBaseModel


class Author(AbstractBaseModel):
    name = models.CharField(max_length=225, db_index=True)
    bio = models.TextField(blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=225, blank=True, null=True, db_index=True)
    website = models.URLField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='author_profiles', blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'nationality']),  # fast composite lookup
        ]


class Publisher(AbstractBaseModel):
    name = models.CharField(max_length=225, db_index=True)
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    website = models.URLField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Genre(AbstractBaseModel):
    name = models.CharField(max_length=225, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    parent_genre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subgenre')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Genres'


class Book(AbstractBaseModel):
    # Core Book Information
    title = models.CharField(max_length=225, db_index=True)
    description = models.TextField(blank=True, null=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    language = models.CharField(max_length=225, default='English', db_index=True)
    cover_image = models.ImageField(upload_to='book_covers', blank=True)
    isbn = models.CharField(max_length=13, unique=True, blank=True, null=True, db_index=True)
    publication_date = models.DateField(null=True, blank=True, db_index=True)
    edition = models.CharField(max_length=50, blank=True, null=True)

    # Relationship for normalization
    # on_delete = CASCADE by default in django for many to many by django
    authors = models.ManyToManyField(Author, related_name='books')
    publisher = models.ForeignKey('Publisher', on_delete=models.PROTECT, related_name='books')
    genres = models.ManyToManyField(Genre, related_name='books', blank=True)

    def __str__(self):
        author_names = ', '.join(author.name for author in self.authors.all())
        return f"{self.title} by {author_names}" if author_names else self.title

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['title', 'publication_date']),
        ]


class Stock(AbstractBaseModel):
    book = models.OneToOneField('Book', on_delete=models.CASCADE, related_name='stock')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                validators=[MinValueValidator(0.00)])
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=False)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
                                              validators=[MinValueValidator(0), MaxValueValidator(100)])
    last_restock_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Stock for {self.book.title} - Quantity: {self.stock_quantity}"

    class Meta:
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['stock_quantity']),
            models.Index(fields=['is_available']),
        ]

    @property
    def discount_amount(self):
        return self.price - self.price_after_discount_one_item

    @property
    def price_after_discount_one_item(self):
        return self.price * (1 - self.discount_percentage / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        if self.stock_quantity is not None:
            self.is_available = self.stock_quantity > 0
        super().save(*args, **kwargs)
