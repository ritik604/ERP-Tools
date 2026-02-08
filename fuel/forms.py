from django import forms
from .models import FuelRecord


class FuelRecordForm(forms.ModelForm):
    """Form for creating and editing fuel records."""
    
    class Meta:
        model = FuelRecord
        fields = [
            'project', 'date', 'fuel_type', 'quantity_liters', 
            'price_per_liter', 'vehicle', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
