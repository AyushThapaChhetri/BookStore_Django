from datetime import datetime, date

from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_future_dates(value):
    if value < timezone.now().date():
        raise ValidationError("Dates must be in future.")


def validate_past_dates(value):
    if value > timezone.now().date():
        raise ValidationError("Dates must be in past.")


def validate_date(value):
    try:
        if isinstance(value, str):
            datetime.strptime(value, "%Y-%m-%d")
        elif isinstance(value, date):
            return value
        else:
            raise ValidationError("Invalid date.")

    except ValueError:
        raise ValidationError("Date must be in YYYY-MM-DD format.")
