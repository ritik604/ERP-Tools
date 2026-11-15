import logging
from datetime import timedelta
from .models import AuditLog
from core.utils import get_ist_now

logger = logging.getLogger(__name__)

def update_audit_log_with_images(module, model_name, record_id, image_names, user=None, ip_address=None, record_repr=None):
    """
    Updates the most recent CREATE audit log entry for a record with image names.
    If no CREATE entry exists within a short window, it creates a new UPDATE entry.
    
    Args:
        module (str): The module name (e.g., 'Fuel', 'Project - Milestone')
        model_name (str): The model name (e.g., 'FuelRecord', 'Milestone')
        record_id (str): The primary key of the record
        image_names (list): List of image filenames
        user (User, optional): The user performing the action
        ip_address (str, optional): The IP address of the user
        record_repr (str, optional): String representation of the record (for new entry)
    """
    if not image_names:
        return

    pipe_separated_names = ' | '.join(image_names)
    image_changes = {
        'images': {
            'old': None,
            'new': pipe_separated_names
        }
    }

    # Find the most recent CREATE audit entry for this record (created within last 10 seconds)
    # We look for CREATE first to append to the initial record creation log
    recent_time = get_ist_now() - timedelta(seconds=10)
    
    try:
        existing_audit = AuditLog.objects.filter(
            module=module,
            model_name=model_name,
            record_id=str(record_id),
            action='CREATE',
            timestamp__gte=recent_time
        ).order_by('-timestamp').first()
        
        if existing_audit:
            # Update existing CREATE entry
            existing_audit.changes.update(image_changes)
            existing_audit.save()
            logger.info(f"Updated CREATE audit log for {model_name} {record_id} with images.")
        else:
            # Fallback: Create a new UPDATE entry if the CREATE entry is missed or too old
            # This ensures we still capture the images even if the transaction timing is off
            if user:
                 AuditLog.objects.create(
                    module=module,
                    model_name=model_name,
                    record_id=str(record_id),
                    record_repr=record_repr or f"{model_name} #{record_id}",
                    action='UPDATE',
                    user=user,
                    changes=image_changes,
                    ip_address=ip_address
                )
                 logger.info(f"Created UPDATE audit log for {model_name} {record_id} with images (CREATE not found).")

    except Exception as e:
        logger.error(f"Failed to update audit log for images: {e}", exc_info=True)
