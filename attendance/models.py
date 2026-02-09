from django.db import models
from users.models import CustomUser
from projects.models import ProjectSite
from core.utils import get_ist_now, get_ist_date

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LEAVE', 'On Leave'),
    )
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='attendance_records')
    site = models.ForeignKey(ProjectSite, on_delete=models.CASCADE, related_name='site_attendance')
    date = models.DateField(default=get_ist_date)
    check_in_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABSENT', db_index=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    verified = models.BooleanField(default=False, help_text="True if location matches site location within 1km")

    class Meta:
        unique_together = ('worker', 'date')
        ordering = ['-date', '-check_in_time']
        indexes = [
            models.Index(fields=['worker', 'date']),
            models.Index(fields=['site', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.worker.username} - {self.date} - {self.status}"

