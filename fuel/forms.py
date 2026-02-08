from django import forms
from .models import FuelRecord


class FuelRecordForm(forms.ModelForm):
    """Form for creating and editing fuel records."""
    
    class Meta:
        model = FuelRecord
        fields = [
            'project', 'date', 'fuel_type', 'quantity_liters', 
            'total_cost', 'price_per_liter', 'vehicle', 'receipt', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'price_per_liter': forms.NumberInput(attrs={'readonly': 'readonly'}),
        }
        labels = {
            'quantity_liters': 'Fuel Quantity (Liters)',
            'total_cost': 'Total Amount Paid (INR)',
            'price_per_liter': 'Rate per Liter (Calculated)',
        }
