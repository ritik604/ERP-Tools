"""
Signal handlers to automatically capture changes across all ERP models.

Robustness Guarantees:
1. No orphan audits: Uses transaction.on_commit() to ensure audit entries
   are only created AFTER main transaction succeeds
2. Graceful fallback: Wraps audit logging in try-except - if audit fails,
   logs to console/file but never blocks the main operation
"""
import logging
from functools import wraps
from django.db import transaction
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from .middleware import get_current_user, get_current_ip

logger = logging.getLogger(__name__)

# Store original values before save (in thread-local-like instance attribute)
_pre_save_cache = {}


def safe_audit_log(func):
    """Decorator to ensure audit logging never blocks main operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Audit logging failed: {e}", exc_info=True)
            # Never raise - audit failure should not block main operation
    return wrapper


def get_model_fields_to_track(model_name):
    """Return list of fields to track for each model."""
    # Define fields to exclude from tracking (auto-generated, internal)
    exclude_fields = {'id', 'pk', 'password', 'last_login', 'created_at', 'updated_at'}
    return exclude_fields


from django.db.models.fields.files import FieldFile
from django.core.files import File

def serialize_value(value):
    """Convert field values to JSON-serializable format."""
    if value is None:
        return None
    if isinstance(value, (FieldFile, File)):
        return str(value)
    if hasattr(value, 'pk'):  # ForeignKey
        return str(value)
    if hasattr(value, 'isoformat'):  # Date/DateTime
        return value.isoformat()
    if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
        return list(value)
    return str(value) if not isinstance(value, (int, float, bool, str)) else value


def get_changes(old_instance, new_instance):
    """Compare old and new instance to get changes."""
    changes = {}
    exclude_fields = get_model_fields_to_track(new_instance.__class__.__name__)
    
    for field in new_instance._meta.fields:
        field_name = field.name
        if field_name in exclude_fields:
            continue
        
        old_value = getattr(old_instance, field_name, None) if old_instance else None
        new_value = getattr(new_instance, field_name, None)
        
        # Serialize for comparison
        old_serialized = serialize_value(old_value)
        new_serialized = serialize_value(new_value)
        
        if old_serialized != new_serialized:
            changes[field_name] = {
                'old': old_serialized,
                'new': new_serialized
            }
    
    return changes


def get_all_values(instance):
    """Get all field values for CREATE action."""
    values = {}
    exclude_fields = get_model_fields_to_track(instance.__class__.__name__)
    
    for field in instance._meta.fields:
        field_name = field.name
        if field_name in exclude_fields:
            continue
        
        value = getattr(instance, field_name, None)
        serialized = serialize_value(value)
        if serialized is not None:
            values[field_name] = {'old': None, 'new': serialized}
    
    return values


@safe_audit_log
def create_audit_log(action, instance, changes=None):
    """Create an audit log entry."""
    from .models import AuditLog
    
    if not changes:
        return
    
    user = get_current_user()
    ip_address = get_current_ip()
    
    # Get module from app label
    module = instance._meta.app_label
    model_name = instance.__class__.__name__
    
    AuditLog.objects.create(
        module=module,
        model_name=model_name,
        record_id=str(instance.pk),
        record_repr=str(instance)[:255],
        action=action,
        user=user,
        changes=changes,
        ip_address=ip_address
    )


# Models to track
TRACKED_MODELS = {
    'users.customuser',
    'fuel.fuelrecord',
    'projects.projectsite',
    'projects.milestone',
    'projects.milestoneimage',
    'attendance.attendance',
    'vehicles.vehicle',
}


def is_tracked_model(instance):
    """Check if this model should be tracked."""
    model_key = f"{instance._meta.app_label}.{instance.__class__.__name__.lower()}"
    return model_key in TRACKED_MODELS


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """Capture old values before save for UPDATE detection."""
    if not is_tracked_model(instance):
        return
    
    if instance.pk:
        try:
            # Fetch the existing instance from database
            old_instance = sender.objects.get(pk=instance.pk)
            # Store in cache using instance id as key
            cache_key = f"{sender.__name__}_{instance.pk}"
            _pre_save_cache[cache_key] = old_instance
        except sender.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Audit pre_save failed: {e}")


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """Log CREATE or UPDATE action after successful save."""
    if not is_tracked_model(instance):
        return
    
    cache_key = f"{sender.__name__}_{instance.pk}"
    
    if created:
        # CREATE action - log all values
        changes = get_all_values(instance)
        action = 'CREATE'
        
        # Use transaction.on_commit to ensure audit only happens after main tx succeeds
        transaction.on_commit(
            lambda: create_audit_log(action, instance, changes)
        )
    else:
        # UPDATE action - log only changed values
        old_instance = _pre_save_cache.pop(cache_key, None)
        if old_instance:
            changes = get_changes(old_instance, instance)
            if changes:  # Only log if there are actual changes
                action = 'UPDATE'
                transaction.on_commit(
                    lambda: create_audit_log(action, instance, changes)
                )


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    """Log DELETE action after successful deletion."""
    if not is_tracked_model(instance):
        return
    
    # Capture all values being deleted
    changes = get_all_values(instance)
    action = 'DELETE'
    
    # Use transaction.on_commit for consistency
    transaction.on_commit(
        lambda: create_audit_log(action, instance, changes)
    )
