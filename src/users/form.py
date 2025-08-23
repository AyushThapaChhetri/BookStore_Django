import os
import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from tailwind.validate import ValidationError

from src.users.models import User


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


class UserForm(UserCreationForm):
    # confirmPassword = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password1',
            # 'confirmPassword',
            'password2',
            'contact_number',
            'date_of_birth',
            'address',
            'profile_picture',
        ]
        widgets = {
            # 'password' : forms.PasswordInput(),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name')
        value = clean_spaces_or_none(value)
        value = not_none_or_number(value)
        if not value:
            raise forms.ValidationError("Please enter a first name.")
        if len(value) < 3:
            raise forms.ValidationError("First name must be at least 3 characters long.")

        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name')
        value = clean_spaces_or_none(value)
        value = not_none_or_number(value)
        if not value:
            raise forms.ValidationError("Please enter a last name.")
        if len(value) < 3:
            raise forms.ValidationError("First name must be at least 3 characters long.")
        return value

    def email(self):
        value = self.cleaned_data.get('email')
        value = clean_spaces_or_none(value)
        value = not_none_or_number(value)
        if not value:
            raise forms.ValidationError("Please enter a email.")
        return value

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > timezone.localdate():
            raise forms.ValidationError("Date of Birth cannot be in the future.")
        return dob

    def clean_contact_number(self):
        value = self.cleaned_data.get('contact_number')
        value = clean_spaces_or_none(value)
        if value and not re.fullmatch(r'\d{7,20}', value):
            raise forms.ValidationError("Enter a valid contact number (digits only, 7-20 digits).")
        return value

    def clean_address(self):
        value = self.cleaned_data.get('address', '')
        value = clean_spaces_or_none(value)
        value = not_none_or_number(value)
        if not value:
            raise forms.ValidationError("Please enter a address.")
        if len(value) < 3:
            raise forms.ValidationError("First name must be at least 3 characters long.")

        return value

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if not image:
            print("No image Provided")
            return None
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


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'autocomplete': 'new-email'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
