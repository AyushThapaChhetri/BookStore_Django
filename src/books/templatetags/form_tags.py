# Create this file: your_app/templatetags/form_tags.py

from django import template
from django.forms.widgets import (
    Textarea, Select, SelectMultiple,
    FileInput, ClearableFileInput, HiddenInput, CheckboxInput, DateInput
)

register = template.Library()


@register.filter
def widget_type(field):
    """
    Returns the widget type as a string for easier template conditionals
    """
    widget = field.field.widget

    if isinstance(widget, (FileInput, ClearableFileInput)):
        return 'file'
    elif isinstance(widget, Textarea):
        return 'textarea'
    elif isinstance(widget, SelectMultiple):
        return 'select_multiple'
    elif isinstance(widget, Select):
        return 'select'
    elif isinstance(widget, HiddenInput):
        return 'hidden'
    elif isinstance(widget, CheckboxInput):
        return 'checkbox'
    elif isinstance(widget, DateInput):
        return 'date'
    else:
        return 'input'


@register.filter
def input_type(field):
    """
    Returns the input type, handling widgets that don't have input_type
    """
    widget = field.field.widget
    return getattr(widget, 'input_type', 'text')
