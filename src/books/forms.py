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
            'language'
            ]

    def clean_description(self):
        desc = self.cleaned_data.get('description','')
        return desc.strip() or None

    def clean_pages(self):
        pages=self.cleaned_data.get('pages')
        return pages if pages not in ['',None] else None