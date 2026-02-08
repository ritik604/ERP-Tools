from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Model to track all changes made across the ERP system.
    Captures CREATE, UPDATE, and DELETE operations with full change history.
    """
    ACTION_CHOICES = (
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
    )
    
    # What was changed
    module = models.CharField(max_length=100, db_index=True)      # e.g., "users", "fuel"
    model_name = models.CharField(max_length=100, db_index=True)  # e.g., "CustomUser"
    record_id = models.CharField(max_length=50)                   # ID of changed record
    record_repr = models.CharField(max_length=255, blank=True)    # String representation
    
    # What action was taken
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, db_index=True)
    
    # Who made the change
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='audit_logs'
    )
    
    # What changed (JSON: {"field": {"old": x, "new": y}})
    changes = models.JSONField(default=dict)
    
    # When and from where
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['module', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        return f"{self.action} {self.model_name} #{self.record_id} by {self.user}"
    
    @property
    def action_icon(self):
        """Return Bootstrap icon class for the action type."""
        icons = {
            'CREATE': 'bi-plus-circle-fill text-success',
            'UPDATE': 'bi-pencil-fill text-primary',
            'DELETE': 'bi-trash-fill text-danger',
        }
        return icons.get(self.action, 'bi-question-circle')
    
    @property
    def action_badge_class(self):
        """Return Bootstrap badge class for the action type."""
        badges = {
            'CREATE': 'bg-success',
            'UPDATE': 'bg-primary',
            'DELETE': 'bg-danger',
        }
        return badges.get(self.action, 'bg-secondary')
