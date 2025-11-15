import re

from django.core.exceptions import ValidationError


def validate_no_special_chars(value):
    if not value.isalnum():
        raise ValidationError("Field must contain letter or numbers only.")


def sanitize_spaces(value):
    cleaned = re.sub(r'\s+', ' ', value).strip()
    return cleaned


def validate_min_length(value, min_length=3):
    if len(value.strip()) < min_length:
        raise ValidationError(f"Field must contain at least {min_length} characters")
