from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower

from src.books.managers import BookManager
from src.core.models import AbstractBaseModel
from src.core.soft_delete import SafeDeleteModel


class Author(AbstractBaseModel):
    name = models.CharField(max_length=225, db_index=True)
    bio = models.TextField(blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=225, db_index=True)
    website = models.URLField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='author_profiles', blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'nationality']),  # fast composite lookup
        ]
        constraints = [
            UniqueConstraint(
                Lower('name'),
                Lower('nationality'),

                name='unique_author_name_nationality_ci'
            )
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
        constraints = [
            UniqueConstraint(
                Lower('name'),
                name='unique_publisher_name_ci'
            )
        ]


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
    publication_date = models.DateField(null=False, blank=False)
    edition = models.CharField(max_length=50, blank=True, null=True)

    # Relationship for normalization
    # on_delete = CASCADE by default in django for many to many by django
    authors = models.ManyToManyField(Author, related_name='books')
    publisher = models.ForeignKey('Publisher', on_delete=models.PROTECT, related_name='books')
    genres = models.ManyToManyField(Genre, related_name='books', blank=True)

    objects = BookManager()

    def __str__(self):
        author_names = ', '.join(author.name for author in self.authors.all())
        return f"{self.title} by {author_names}" if author_names else self.title

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['title', 'publication_date']),
        ]
        constraints = [
            UniqueConstraint(
                fields=['title', 'publication_date', 'publisher'],
                name='unique_book_title_pubdate_publisher'
            )
        ]
