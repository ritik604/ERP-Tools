from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_id', 'name', 'plate_number', 'vehicle_type', 'assigned_site', 'status', 'last_maintenance_date')
    list_filter = ('status', 'vehicle_type', 'assigned_site')
    search_fields = ('vehicle_id', 'name', 'plate_number')
    ordering = ('-created_at',)
