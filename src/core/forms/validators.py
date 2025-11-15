from django.core.exceptions import ValidationError


def validate_value_required(value):
    if value is None:
        raise ValidationError('This field is required')


def validate_percentage(value):
    validate_value_required(value)

    if value < 0 or value > 100:
        raise ValidationError('Discount percentage must be between 0 and 100')


def validate_no_leading_trailing_spaces(value):
    validate_value_required(value)

    if isinstance(value, str):
        if value != value.strip():
            raise ValidationError('Text cannot have leading or trailing whitespace')
