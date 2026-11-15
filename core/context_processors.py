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
    
    if request.user.is_authenticated:
        today = get_ist_date()
        # Check if any attendance record exists for today (PRESENT, LEAVE, etc.)
        exists = Attendance.objects.filter(worker=request.user, date=today).exists()
        context['attendance_marked'] = exists
        
        # Auto-popup prompt to direct user to Face Scanner check-in
        if not exists:
            context['show_attendance_popup'] = True
            
    return context
