import os
from decimal import Decimal, ROUND_DOWN

from django import forms
from django.core.exceptions import ValidationError

from src.books.models import Book


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

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        return desc.strip() or None

    def clean_pages(self):
        pages = self.cleaned_data.get('pages')
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
