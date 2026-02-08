from django.db import models, transaction
from django.utils import timezone
from projects.models import ProjectSite

class Vehicle(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('MAINTENANCE', 'Maintenance'),
        ('INACTIVE', 'Inactive'),
    )
    
    VEHICLE_TYPE_CHOICES = (
        ('TRUCK', 'Truck'),
        ('EXCAVATOR', 'Excavator'),
        ('CRANE', 'Crane'),
        ('LOADER', 'Loader'),
        ('OTHER', 'Other'),
    )

    vehicle_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='TRUCK')
    
    asset_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    assigned_site = models.ForeignKey(ProjectSite, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_vehicles')
    
    last_maintenance_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['assigned_site']),
            models.Index(fields=['vehicle_type']),
        ]

    def save(self, *args, **kwargs):
        if not self.vehicle_id:
            with transaction.atomic():
                # Get the last vehicle ID in a thread-safe way
                last_vehicle = Vehicle.objects.select_for_update().order_by('-id').first()
                if last_vehicle and last_vehicle.id:
                    last_id = int(last_vehicle.id)
                else:
                    last_id = 0
                self.vehicle_id = f"VEH-{last_id + 1:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.plate_number})"
