from datetime import datetime

from django.core.exceptions import ValidationError


def validate_date_range(from_date_str, to_date_str, date_format="%Y-%m-%d"):
    print("validate_date_range called with:", from_date_str, to_date_str)

    if not from_date_str and not to_date_str:
        return None, None

    errors = {}
    from_date = None
    to_date = None

    if not from_date_str:
        errors['from'] = "From date must be provided."
    else:
        try:
            print("Parsing from_date:", from_date_str)
            from_date = datetime.strptime(from_date_str, date_format).date()
        except ValueError:
            print("Failed to parse from_date")
            errors['from'] = f"'From' date is not a valid date. Expected format: {date_format}"

    if not to_date_str:
        errors['to'] = "To date must be provided."
    else:
        try:

            to_date = datetime.strptime(to_date_str, date_format).date()
        except ValueError:
            errors['to'] = f"'To' date is not a valid date. Expected format: {date_format}"

    if from_date and to_date and from_date > to_date:
        errors['from'] = "'From' date cannot be later than 'To' date."
        errors['to'] = "'To' date cannot be earlier than 'From' date."

    if errors:
        raise ValidationError(errors)

    return from_date, to_date
