import os
import re
from decimal import Decimal, ROUND_DOWN

from django import forms
from django.core.exceptions import ValidationError

from src.books.models import Book


def clean_spaces_or_none(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r'\s+', ' ', value).strip()
    return cleaned if cleaned else None


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'publisher',
            'description',
            'pages',
            'language',
            'price',
            'stock_quantity',
            'cover_image',
        ]
        widgets = {
            'cover_image': forms.ClearableFileInput(),
            'price': forms.TextInput(attrs={'placeholder': 'e.g. 39.99'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        return clean_spaces_or_none(title)

    def clean_author(self):
        author = self.cleaned_data.get('author')
        return clean_spaces_or_none(author)

    def clean_publisher(self):
        publisher = self.cleaned_data.get('publisher')
        return clean_spaces_or_none(publisher)

    def clean_language(self):
        language = clean_spaces_or_none(self.cleaned_data.get('language'))

        if language is not None and language.isdigit():
            raise forms.ValidationError("Language cannot be a number.")

        return language

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        return desc.strip() or None

    def clean_pages(self):
        pages = self.cleaned_data.get('pages')

        if pages == 0:
            raise forms.ValidationError("Pages cannot be zero.")

        return pages if pages not in ['', None] else None

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price in [None, '']:
            return None  # store as NULL in DB
        try:
            price = Decimal(price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        except (ValueError, TypeError):
            raise forms.ValidationError("Enter a valid price (e.g., 39.99)")
        if price < 0:
            raise forms.ValidationError("Price must be positive")
        return price

    def clean_stock_quantity(self):
        stock = self.cleaned_data.get('stock_quantity')

        # Convert empty string to None if the field is optional
        if stock in ['', None]:
            return None

        if stock < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")

        return stock

    def clean_cover_image(self):
        image = self.cleaned_data.get('cover_image')
        if not image:
            print("No image provided")
            return None

        print("Image provided")
        valid_extenstions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(image.name)[1]
        if ext not in valid_extenstions:
            raise ValidationError("Only JPG, JPEG, PNG, GIF, and WEBP images are allowed.")

        valid_mime_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if hasattr(image, 'content_type') and image.content_type not in valid_mime_types:
            raise ValidationError("Only JPG, JPEG, PNG, and GIF files are allowed.")

        max_size = 2 * 1024 * 1024
        if image.size > max_size:
            raise ValidationError("Image too large (max 2MB).")

        return image
