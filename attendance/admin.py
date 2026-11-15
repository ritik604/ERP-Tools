from django.contrib import admin
from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('worker', 'site', 'date', 'status', 'check_in_time', 'verification_mode', 'verified', 'face_verified')
    list_filter = ('status', 'date', 'verification_mode', 'verified', 'face_verified', 'site')
    search_fields = ('worker__username', 'worker__first_name', 'worker__last_name', 'worker__employee_id', 'site__name')
    date_hierarchy = 'date'
    ordering = ('-date', '-check_in_time')
