from django import forms
from .models import FuelRecord


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget to handle multiple file uploads."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field to handle multiple file uploads."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={
            'accept': 'image/*',
            'class': 'form-control'
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class FuelRecordForm(forms.ModelForm):
    """Form for creating and editing fuel records."""
    
    # Multiple images field (not tied to model)
    images = MultipleFileField(required=False, label='Receipt Images')
    
    class Meta:
        model = FuelRecord
        fields = [
            'project', 'date', 'fuel_type', 'quantity_liters', 
            'total_cost', 'price_per_liter', 'vehicle', 'notes'
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
