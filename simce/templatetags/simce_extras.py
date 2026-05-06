from django import template

register = template.Library()


@register.filter
def replace(value, arg):
    """{{ value|replace:'_: ' }} → replaces first char with second."""
    old, new = arg.split(':', 1) if ':' in arg else (arg, '')
    return str(value).replace(old, new)
