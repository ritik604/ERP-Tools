from django import template
from django.utils import timezone
from zoneinfo import ZoneInfo

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
        from datetime import datetime
        ist = ZoneInfo('Asia/Kolkata')
        
        # If it's a datetime (which is a subclass of date), handle timezone
        if isinstance(value, datetime):
            if timezone.is_aware(value):
                value = value.astimezone(ist)
            else:
                value = value.replace(tzinfo=ist)
        
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
        ist = ZoneInfo('Asia/Kolkata')
        
        if timezone.is_aware(value):
            # Convert to IST
            value = value.astimezone(ist)
        else:
            # If naive, make it aware in IST
            value = value.replace(tzinfo=ist)
        
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
        from datetime import datetime, time
        ist = ZoneInfo('Asia/Kolkata')
        
        # If it's a datetime, convert to IST first
        if isinstance(value, datetime):
            if timezone.is_aware(value):
                value = value.astimezone(ist)
            else:
                value = value.replace(tzinfo=ist)
            value = value.time()
        elif isinstance(value, time):
            # If it's just a time object, we assume it's naive
            pass

        # Format as '01:57 PM'
        # To use strftime on time, we combine with today's date
        dt = datetime.combine(datetime.today(), value)
        return dt.strftime('%I:%M %p')
    except (ValueError, TypeError, AttributeError):
        return value

