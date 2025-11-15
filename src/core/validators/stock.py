from django.core.exceptions import ValidationError


def validate_current_price(value):
    if value is None:
        raise ValidationError('Current price is required')

    if value < 0:
        raise ValidationError('Current price cannot be negative')

    if value < 1:
        raise ValidationError('Current price must be set')
