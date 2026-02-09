from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp_ist', 'action', 'module', 'model_name', 'user', 'record_id')
    list_filter = ('action', 'module', 'user', 'timestamp')
    search_fields = ('module', 'model_name', 'record_id', 'record_repr', 'changes')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'action', 'module', 'model_name', 'record_id', 'record_repr', 'user', 'changes', 'ip_address')

    def timestamp_ist(self, obj):
        # Already naive IST, but let's label it clearly
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S IST')
    timestamp_ist.short_description = 'Timestamp (IST)'
    timestamp_ist.admin_order_field = 'timestamp'
