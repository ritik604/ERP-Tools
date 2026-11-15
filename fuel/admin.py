from django.contrib import admin
from .models import FuelRecord, FuelRecordImage

class FuelRecordImageInline(admin.TabularInline):
    model = FuelRecordImage
    extra = 0

@admin.register(FuelRecord)
class FuelRecordAdmin(admin.ModelAdmin):
    list_display = ('record_id', 'project', 'date', 'fuel_type', 'quantity_liters', 'price_per_liter', 'total_cost')
    list_filter = ('fuel_type', 'date', 'project')
    search_fields = ('record_id', 'project__name')
    date_hierarchy = 'date'
    ordering = ('-date',)
    inlines = [FuelRecordImageInline]
