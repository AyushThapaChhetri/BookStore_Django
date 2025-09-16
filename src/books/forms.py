import datetime
import os
import re

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from src.books.models import Book, Author, Genre, Publisher, Stock


def clean_spaces_or_none(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r'\s+', ' ', value).strip()
    return cleaned if cleaned else None


def validate_isbn(isbn: str) -> bool:
    """Validate ISBN-13: strip non-digits, check length 13, starts with 978/979, and checksum."""
    d = re.sub(r'\D', '', isbn).strip()
    print("Digits:", list(d))  # debug

    if len(d) != 13 or not d.isdigit():
        return False
    if not d.startswith(('978', '979')):
        return False

    # Take only the first 12 digits.
    # Multiply alternate digits by 1 or 3.
    # Compute the check digit (13th digit).
    # Compare it with the given last digit.
    digits = [int(x) for x in d]
    check_digit = digits[-1]  # last digit
    body = digits[:-1]  # first 12 digits

    total = sum(body[::2]) + sum(x * 3 for x in body[1::2])
    expected = (10 - (total % 10)) % 10

    return check_digit == expected


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = [
            'name',
            'bio',
            'birth_date',
            'death_date',
            'nationality',
            'website',
            'profile_image',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'profile_image': forms.ClearableFileInput(),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'death_date': forms.DateInput(attrs={'type': 'date'}),
            'website': forms.URLInput(attrs={'type': 'url'}),
        }

    def clean_name(self):
        name = clean_spaces_or_none(self.cleaned_data.get('name'))

        if not name or len(name) < 5:
            raise forms.ValidationError('Name must be at least 5 characters long.')
        return name

    def clean_bio(self):
        bio = self.cleaned_data.get('bio', '')
        return bio.strip() or None

    def clean_nationality(self):
        name = clean_spaces_or_none(self.cleaned_data.get('name'))
        nationality = clean_spaces_or_none(self.cleaned_data.get('nationality'))

        if name and nationality:
            # Exclude current instance when checking duplicates
            qs = Author.objects.filter(
                Q(name__iexact=name) & Q(nationality__iexact=nationality)
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError('This author already exists.')

        return nationality

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date and birth_date > datetime.date.today():
            raise ValidationError("Birth date must be Future Dates")
        return birth_date

    def clean_death_date(self):

        death_date = self.cleaned_data.get('death_date')
        if death_date and death_date > datetime.date.today():
            raise ValidationError("Death date cannot be in the future.")

        # also ensure death date is not before birth date
        birth_date = self.cleaned_data.get('birth_date')
        if death_date and birth_date and death_date < birth_date:
            raise ValidationError("Death date cannot be earlier than birth date.")

        return death_date

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')
        if not image:
            return None
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in valid_extensions:
            raise ValidationError("Only JPG, JPEG, PNG, GIF, and WEBP images are allowed.")
        valid_mime_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
            raise ValidationError("Invalid image file type.")
        max_size = 2 * 1024 * 1024  # 2MB
        if image.size > max_size:
            raise ValidationError("Image too large (max 2MB).")
        return image


class PublisherForm(forms.ModelForm):
    class Meta:
        model = Publisher
        fields = [
            'name',
            'founded_year',
            'website',
            'address',
            'contact_email',
            'description',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            # 'address': forms.Textarea(attrs={'rows': 3}),
            'address': forms.TextInput(attrs={
                'placeholder': 'Address',
            }),

        }

    def clean_name(self):
        name = clean_spaces_or_none(self.cleaned_data.get('name'))
        if name:
            qs = Publisher.objects.filter(name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise ValidationError("A publisher with this name already exists.")
        return name

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        return desc.strip() or None

    def clean_address(self):
        addr = self.cleaned_data.get('address', '')
        return addr.strip() or None

    def clean_founded_year(self):
        year = self.cleaned_data.get('founded_year')
        current_year = datetime.date.today().year
        if year is not None and (year < 1000 or year > current_year):
            raise ValidationError(f"Founded year must be between 1000 and {current_year}.")
        return year

    def clean_contact_email(self):
        return clean_spaces_or_none(self.cleaned_data.get('contact_email'))


class GenreForm(forms.ModelForm):
    class Meta:
        model = Genre
        fields = [
            'name',
            'description',
            'parent_genre'
        ]

    def clean_name(self):
        return clean_spaces_or_none(self.cleaned_data.get('name'))

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        return desc.strip() or None

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent_genre')
        name = cleaned_data.get('name')
        if parent and parent.name == name:
            raise ValidationError("A genre cannot be its own parent.")
        return cleaned_data


class BookForm(forms.ModelForm):
    isbn = forms.CharField(required=False)  # override, skip default max_length check

    class Meta:
        model = Book
        fields = [
            'title',
            'description',
            'pages',
            'language',
            'cover_image',
            'isbn',
            'publication_date',
            'edition',
            'authors',
            'publisher',
            'genres',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'cover_image': forms.ClearableFileInput(),
            'authors': forms.SelectMultiple(),
            'genres': forms.SelectMultiple(),
            # 'publication_date': forms.DateInput(attrs={'type': 'date'}),
            'publication_date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d'
            ),

        }

    def clean_title(self):
        return clean_spaces_or_none(self.cleaned_data.get('title'))

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        return desc.strip() or None

    def clean_language(self):
        language = clean_spaces_or_none(self.cleaned_data.get('language'))
        if language and language.isdigit():
            raise ValidationError("Language cannot be a number.")
        return language

    def clean_pages(self):
        pages = self.cleaned_data.get('pages')
        if pages == 0:
            raise ValidationError("Pages cannot be zero.")
        return pages if pages is not None else None

    def clean_isbn(self):
        isbn = self.cleaned_data.get('isbn')
        if not isbn:
            return None
        cleaned_isbn = re.sub(r'\D', '', isbn).strip()  # Strip non-digits for storage
        print("Validating ISBN:", repr(cleaned_isbn))
        print(cleaned_isbn)
        if not validate_isbn(cleaned_isbn):
            print('invalid ISBN')
            raise ValidationError("Invalid ISBN-13 format or checksum.")
        print('correct Isbn')
        return cleaned_isbn  # Store without hyphens

    def clean_edition(self):
        return clean_spaces_or_none(self.cleaned_data.get('edition'))

    def clean_cover_image(self):
        image = self.cleaned_data.get('cover_image')
        if not image:
            return None
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(image.name)[1].lower()
        if ext not in valid_extensions:
            raise ValidationError("Only JPG, JPEG, PNG, GIF, and WEBP images are allowed.")
        valid_mime_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
            raise ValidationError("Invalid image file type.")
        max_size = 2 * 1024 * 1024  # 2MB
        if image.size > max_size:
            raise ValidationError("Image too large (max 2MB).")
        return image

    def clean_publisher(self):
        publisher = self.cleaned_data.get('publisher')

        if not publisher:
            raise ValidationError("Please select a publisher.")

        return publisher

    def clean_publication_date(self):
        pub_date = self.cleaned_data.get('publication_date')

        if not pub_date:
            return None

            # Ensure it's a date object
        if not isinstance(pub_date, (datetime.date,)):
            raise ValidationError("Invalid date format.")

        # Check if the date is in the future
        today = timezone.localdate()
        if pub_date > today:
            raise ValidationError("Publication date cannot be in the future.")

        return pub_date

    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        publication_date = cleaned_data.get('publication_date')
        publisher = cleaned_data.get('publisher')

        if title and publication_date and publisher:
            qs = Book.objects.filter(
                title__iexact=title,
                publication_date=publication_date,
                publisher=publisher,
            )
            # If you’re editing an existing Book → self.instance.pk is the primary key of that Book.,updating a book, you don’t want Django to think your current record is a “duplicate of itself”.
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            # Returns True if there’s at least one row matching.
            if qs.exists():
                self.add_error('title', 'A book with this Title, Publication Date, and Publisher already exists.')

        return cleaned_data


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = [
            'book',
            'price',
            'stock_quantity',
            'is_available',
            'discount_percentage',
            'last_restock_date',
        ]
        widgets = {
            'price': forms.NumberInput(attrs={'step': '0.01'}),
            'discount_percentage': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'last_restock_date': forms.DateInput(attrs={'type': 'date'}),
            'book': forms.HiddenInput(),  # Often hidden if creating via Book
            'is_available': forms.HiddenInput(),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price < 0:
            raise ValidationError("Price must be non-negative.")
        return price

    def clean_stock_quantity(self):
        quantity = self.cleaned_data.get('stock_quantity')
        if quantity < 0:
            raise ValidationError("Stock quantity cannot be negative.")
        return quantity

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount < 0 or discount > 100:
            raise ValidationError("Discount percentage must be between 0 and 100.")
        return discount

    def clean_last_restock_date(self):
        restock_date = self.cleaned_data.get('last_restock_date')
        if restock_date:
            today = timezone.localdate()
            if restock_date > today:
                raise ValidationError("Restock date cannot be in the future.")
            return restock_date

# class BookForm(forms.ModelForm):
#     class Meta:
#         model = Book
#         fields = [
#             'title',
#             'author',
#             'publisher',
#             'description',
#             'pages',
#             'language',
#             'price',
#             'stock_quantity',
#             'cover_image',
#         ]
#         widgets = {
#             'cover_image': forms.ClearableFileInput(),
#             'price': forms.TextInput(attrs={'placeholder': 'e.g. 39.99'}),
#         }
#
#     def clean_title(self):
#         title = self.cleaned_data.get('title')
#         return clean_spaces_or_none(title)
#
#     def clean_author(self):
#         author = self.cleaned_data.get('author')
#         return clean_spaces_or_none(author)
#
#     def clean_publisher(self):
#         publisher = self.cleaned_data.get('publisher')
#         return clean_spaces_or_none(publisher)
#
#     def clean_language(self):
#         language = clean_spaces_or_none(self.cleaned_data.get('language'))
#
#         if language is not None and language.isdigit():
#             raise forms.ValidationError("Language cannot be a number.")
#
#         return language
#
#     def clean_description(self):
#         desc = self.cleaned_data.get('description', '')
#         return desc.strip() or None
#
#     def clean_pages(self):
#         pages = self.cleaned_data.get('pages')
#
#         if pages == 0:
#             raise forms.ValidationError("Pages cannot be zero.")
#
#         return pages if pages not in ['', None] else None
#
#     def clean_price(self):
#         price = self.cleaned_data.get('price')
#         if price in [None, '']:
#             return None  # store as NULL in DB
#         try:
#             price = Decimal(price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
#         except (ValueError, TypeError):
#             raise forms.ValidationError("Enter a valid price (e.g., 39.99)")
#         if price < 0:
#             raise forms.ValidationError("Price must be positive")
#         return price
#
#     def clean_stock_quantity(self):
#         stock = self.cleaned_data.get('stock_quantity')
#
#         # Convert empty string to None if the field is optional
#         if stock in ['', None]:
#             return None
#
#         if stock < 0:
#             raise forms.ValidationError("Stock quantity cannot be negative.")
#
#         return stock
#
#     def clean_cover_image(self):
#         image = self.cleaned_data.get('cover_image')
#         if not image:
#             print("No image provided")
#             return None
#
#         print("Image provided")
#         valid_extenstions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
#         ext = os.path.splitext(image.name)[1]
#         if ext not in valid_extenstions:
#             raise ValidationError("Only JPG, JPEG, PNG, GIF, and WEBP images are allowed.")
#
#         valid_mime_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
#         if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
#             raise ValidationError("Only JPG, JPEG, PNG, and GIF files are allowed.")
#
#         max_size = 2 * 1024 * 1024
#         if image.size > max_size:
#             raise ValidationError("Image too large (max 2MB).")
#
#         return image
