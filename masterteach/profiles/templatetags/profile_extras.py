from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter
def div(value, arg):
    """Divide the value by the argument"""
    try:
        return floatformat(float(value) / float(arg), 0)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return floatformat(float(value) * float(arg), 0)
    except (ValueError, TypeError):
        return 0 