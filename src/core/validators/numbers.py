from django.core.exceptions import ValidationError


def validate_number(value):
    if not value.isdigit():
        raise ValidationError("Field must be a number.")


def validate_positive_integer(value):
    if value < 0:
        raise ValidationError("Field must be a positive integer.")


def validate_discount_percentage(value):
    if value < 0 or value > 100:
        raise ValidationError("Discount percentage must be between 0 and 100.")


def validate_minimum_stock(value):
    if value < 1:
        raise ValidationError("Minimum stock must be at least 1.")
