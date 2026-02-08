from django import forms
from .models import Vehicle
from projects.models import ProjectSite

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'name', 'plate_number', 'vehicle_type', 
            'asset_cost', 'assigned_site', 
            'last_maintenance_date', 'status'
        ]
        widgets = {
            'last_maintenance_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Add special class for the select fields if needed
        self.fields['vehicle_type'].widget.attrs.update({'class': 'form-select'})
        self.fields['assigned_site'].widget.attrs.update({'class': 'form-select'})
        self.fields['status'].widget.attrs.update({'class': 'form-select'})
