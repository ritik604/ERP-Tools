from django import template
from django.utils import timezone
import pytz

register = template.Library()

@register.filter
def format_date(value):
    """
    Formats a date as '09 Feb 2026'
    Usage: {{ value|format_date }}
    Example: 2026-02-09 -> 09 Feb 2026
    """
    if value is None or value == "":
        return "-"
    try:
        # If it's a datetime, convert to date
        if hasattr(value, 'date'):
            value = value.date()
        # Format as '09 Feb 2026'
        return value.strftime('%d %b %Y')
    except (ValueError, TypeError, AttributeError):
        return value

@register.filter
def format_datetime(value):
    """
    Formats a datetime as '09 Feb 2026, 01:57:16 IST'
    Usage: {{ value|format_datetime }}
    Example: 2026-02-09 01:57:16 -> 09 Feb 2026, 01:57:16 IST
    """
    if value is None or value == "":
        return "-"
    try:
        # Ensure the datetime is timezone-aware and in IST
        if timezone.is_aware(value):
            ist = pytz.timezone('Asia/Kolkata')
            value = value.astimezone(ist)
        else:
            # If naive, assume it's already in IST
            ist = pytz.timezone('Asia/Kolkata')
            value = ist.localize(value)
        
        # Format as '09 Feb 2026, 01:57:16 IST'
        return value.strftime('%d %b %Y, %H:%M:%S IST')
    except (ValueError, TypeError, AttributeError):
        return value

@register.filter
def format_time(value):
    """
    Formats a time as '01:57 PM'
    Usage: {{ value|format_time }}
    Example: 13:57:16 -> 01:57 PM
    """
    if value is None or value == "":
        return "-"
    try:
        # If it's a datetime, extract the time
        if hasattr(value, 'time'):
            value = value.time()
        # Format as '01:57 PM'
        from datetime import datetime
        dt = datetime.combine(datetime.today(), value)
        return dt.strftime('%I:%M %p')
    except (ValueError, TypeError, AttributeError):
        return value
