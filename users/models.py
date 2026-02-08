from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models, transaction
from django.utils import timezone

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields['role'] = 'ADMIN'
        return super().create_superuser(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('SUPERVISOR', 'Supervisor'),
        ('WORKER', 'Worker'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='WORKER', db_index=True)
    employee_id = models.CharField(max_length=20, unique=True, editable=False)
    government_id = models.CharField(max_length=50, blank=True, null=True, help_text="Aadhar/SSN etc.")
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    date_joined = models.DateField(default=timezone.localdate)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_site = models.ForeignKey('projects.ProjectSite', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_workers')

    class Meta:
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['assigned_site']),
        ]
    
    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.employee_id:
            with transaction.atomic():
                # Get the last employee ID in a thread-safe way
                last_user = CustomUser.objects.select_for_update().order_by('-id').first()
                if last_user and last_user.id:
                    last_id = int(last_user.id)
                else:
                    last_id = 0
                self.employee_id = f"EMP-{last_id + 1:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

