import re

from django import forms

from src.shipping.models import DeliveryInfo


def clean_spaces_or_none(value: str | None) -> str | None:
    """Strip leading/trailing spaces, collapse multiple spaces, return None if empty."""
    if not value:
        return None
    cleaned = re.sub(r'\s+', ' ', value).strip()
    return cleaned if cleaned else None


def not_none_or_number(value: str | None) -> str | None:
    """Raise ValidationError if value is purely numeric (int or float)."""
    if value:
        cleaned = value.strip()
        try:
            float(cleaned)  # Try converting to number
            raise forms.ValidationError("Please enter a value, not a number.")
        except ValueError:
            pass  # Not a number, OK
    return value


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = DeliveryInfo
        fields = [
            'full_name',
            'country',
            'street_address',
            'city',
            'state',
            'zip_code',
            'phone_number',
        ]

    # Full Name
    def clean_full_name(self):
        value = self.cleaned_data.get('full_name')
        value = clean_spaces_or_none(value)
        value = not_none_or_number(value)
        if not value:
            raise forms.ValidationError("Please enter a full name.")
        return value

    # Country
    def clean_country(self):
        value = self.cleaned_data.get('country')
        value = clean_spaces_or_none(value)
        value = not_none_or_number(value)
        return value

    # Street Address
    def clean_street_address(self):
        value = self.cleaned_data.get('street_address')
        return clean_spaces_or_none(value)

    # City
    def clean_city(self):
        value = self.cleaned_data.get('city')
        value = clean_spaces_or_none(value)
        value = not_none_or_number(value)
        return value

    # State
    def clean_state(self):
        value = self.cleaned_data.get('state')
        return clean_spaces_or_none(value)

    # Zip Code
    def clean_zip_code(self):
        value = clean_spaces_or_none(self.cleaned_data.get('zip_code'))
        if value and not re.fullmatch(r'\d{4,10}', value):
            raise forms.ValidationError("Enter a valid zip code (digits only).")
        return value

    # Phone Number
    def clean_phone_number(self):
        value = clean_spaces_or_none(self.cleaned_data.get('phone_number'))
        if value and not re.fullmatch(r'\d{7,20}', value):
            raise forms.ValidationError("Enter a valid phone number (digits only, 7-20 digits).")
        return value
