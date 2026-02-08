from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    date_joined = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        help_text="Employee joining date"
    )
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'first_name', 'last_name', 'government_id', 'salary', 'mobile', 'assigned_site', 'date_joined')

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        
        # If the person creating the user is a supervisor, only show "Worker" choice
        if request_user and request_user.role == 'SUPERVISOR':
            self.fields['role'].choices = [('WORKER', 'Worker')]
            self.fields['role'].initial = 'WORKER'
        
        self.fields['role'].help_text = "Select role: Admin, Supervisor, or Worker"
        self.fields['assigned_site'].help_text = "Assign a project site immediately (Optional)"

    def clean_date_joined(self):
        date = self.cleaned_data.get('date_joined')
        if not date:
            return timezone.localdate()
        return date

class CustomUserUpdateForm(forms.ModelForm):
    date_joined = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'role', 'government_id', 'salary', 'mobile', 'assigned_site', 'date_joined')

    def clean_date_joined(self):
        date = self.cleaned_data.get('date_joined')
        if not date:
            return self.instance.date_joined or timezone.localdate()
        return date
