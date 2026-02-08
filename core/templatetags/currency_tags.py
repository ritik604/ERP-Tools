from django import template

register = template.Library()

@register.filter
def to_inr(value):
    """
    Formats a number as INR currency with 2 decimal places and commas.
    Usage: {{ value|to_inr }}
    Example: 123456.789 -> INR 123,456.79
    """
    if value is None or value == "":
        return "-"
    try:
        val = float(value)
        # Format with 2 decimal places and commas (standard thousands separator)
        formatted_val = "{:,.2f}".format(val)
        return f"INR {formatted_val}"
    except (ValueError, TypeError):
        return value
