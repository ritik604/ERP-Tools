from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from core.utils import get_ist_now, get_ist_date

class ProjectSite(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('ON_HOLD', 'On Hold'),
    )
    site_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    latitude = models.FloatField(
        help_text="Latitude for geolocation",
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        help_text="Longitude for geolocation",
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    budget = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    start_date = models.DateField(default=get_ist_date)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    site_radius = models.PositiveIntegerField(
        default=500, 
        help_text="Proximity radius in meters for worker check-in"
    )
    
    # Placeholders for future modules
    # material_expense = ...
    # fuel_consumed = ...

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
        ]

    def save(self, *args, **kwargs):
        if not self.site_id:
            with transaction.atomic():
                # Get the last site ID in a thread-safe way
                last_site = ProjectSite.objects.select_for_update().order_by('-id').first()
                if last_site and last_site.id:
                    last_id = int(last_site.id)
                else:
                    last_id = 0
                self.site_id = f"SITE-{last_id + 1:03d}"
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.name} ({self.site_id})"

class Milestone(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )
    project = models.ForeignKey(ProjectSite, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    progress = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    image = models.ImageField(upload_to='milestone_images/', blank=True, null=True)

    class Meta:
        ordering = ['deadline']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['deadline']),
        ]

    def __str__(self):
        return f"{self.name} - {self.project.name}"

class MilestoneImage(models.Model):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='milestone_images/')
    uploaded_at = models.DateTimeField(default=get_ist_now, editable=False)

    def __str__(self):
        return f"Image for {self.milestone.name}"
