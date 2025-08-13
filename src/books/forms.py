from django import forms

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
        }

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        return desc.strip() or None

    def clean_pages(self):
        pages = self.cleaned_data.get('pages')
        return pages if pages not in ['', None] else None

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Price must be positive')
        return price

    def clean_cover_image(self):
        image = self.cleaned_data.get('cover_image')
        return image or None
