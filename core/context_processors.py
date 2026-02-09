from attendance.models import Attendance
from core.utils import get_ist_date

def attendance_status(request):
    """
    Context processor to check if the current user has marked attendance today.
    """
    context = {
        'attendance_marked': False,
        'show_attendance_popup': False
    }
    
    if request.user.is_authenticated and request.user.role in ['BASIC', 'ELEVATED']:
        today = get_ist_date()
        # Check if any attendance record exists for today (PRESENT, LEAVE, etc.)
        exists = Attendance.objects.filter(worker=request.user, date=today).exists()
        context['attendance_marked'] = exists
        
        # Logic for auto-popup: 
        # If not marked, we want to show the popup.
        # We can refine this to only show on specific pages if needed, 
        # but the request says "Checkin button to open a popup... The popup should open when ... login"
        if not exists:
            context['show_attendance_popup'] = True
            
    return context
