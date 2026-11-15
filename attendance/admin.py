from django.contrib import admin
from django.utils.html import format_html
from .models import Attendance

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('worker', 'site', 'date', 'status', 'check_in_time', 'verification_mode', 'verified', 'face_verified', 'liveness_verified', 'photo_thumbnail')
    list_filter = ('status', 'date', 'verification_mode', 'verified', 'face_verified', 'liveness_verified', 'site')
    search_fields = ('worker__username', 'worker__first_name', 'worker__last_name', 'worker__employee_id', 'site__name')
    date_hierarchy = 'date'
    ordering = ('-date', '-check_in_time')
    readonly_fields = ('photo_preview_large',)

    def photo_thumbnail(self, obj):
        if obj.check_in_photo:
            return format_html('<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 1px solid #ccc;" />', obj.check_in_photo.url)
        return "-"
    photo_thumbnail.short_description = 'Check-in Photo'

    def photo_preview_large(self, obj):
        if obj.check_in_photo:
            return format_html('<img src="{}" style="max-width: 320px; border-radius: 8px; border: 1px solid #ddd;" />', obj.check_in_photo.url)
        return "No photo captured"
    photo_preview_large.short_description = 'Check-in Audit Photo'
