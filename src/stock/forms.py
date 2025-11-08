from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Stock, StockBatch


class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = [
            'book',
            'current_price',
            'current_discount_percentage',
            'is_available',
            'last_restock_date',
        ]
        widgets = {
            'current_price': forms.NumberInput(attrs={'step': '0.01'}),
            'current_discount_percentage': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'last_restock_date': forms.DateInput(attrs={'type': 'date'}),
            'book': forms.HiddenInput(),  # Often hidden if creating via Book
            'is_available': forms.HiddenInput(),
        }

    def clean_current_price(self):
        price = self.cleaned_data.get('current_price')
        if price < 0:
            raise ValidationError("Price must be non-negative.")
        return price

    def clean_current_discount_percentage(self):
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


class RestockForm(forms.ModelForm):
    class Meta:
        model = StockBatch
        # fields = ('initial_quantity', 'unit_cost', 'supplier', 'notes', 'received_date')
        fields = ['initial_quantity', 'unit_cost', 'notes', 'received_date']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 5}),
            'received_date': forms.DateInput(attrs={'type': 'date'}), }


class PriceUpdateForm(forms.ModelForm):
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    class Meta:
        model = Stock
        fields = ('current_price', 'current_discount_percentage')
