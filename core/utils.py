from datetime import datetime
from zoneinfo import ZoneInfo
from django.utils import timezone

def get_ist_now():
    """Returns the current IST time as a naive datetime object."""
    return datetime.now(ZoneInfo('Asia/Kolkata')).replace(tzinfo=None)

def get_ist_date():
    """Returns the current IST date."""
    return get_ist_now().date()
