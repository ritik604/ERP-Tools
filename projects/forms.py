from django import forms
from .models import ProjectSite, Milestone

class ProjectSiteForm(forms.ModelForm):
    class Meta:
        model = ProjectSite
        fields = ['name', 'latitude', 'longitude', 'budget', 'site_radius', 'start_date', 'end_date', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'multiple': True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class MilestoneForm(forms.ModelForm):
    images = MultipleFileField(required=False)

    class Meta:
        model = Milestone
        fields = ['name', 'description', 'deadline', 'status', 'progress']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }
