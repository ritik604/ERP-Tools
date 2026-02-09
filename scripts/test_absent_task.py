import os
import sys
import django
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from core.utils import get_ist_date
from datetime import timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "construction_erp.settings")
django.setup()

from users.models import CustomUser
from attendance.models import Attendance
from audit.models import AuditLog
from projects.models import ProjectSite

def run_test():
    print("Setting up test data...")
    # Create a test site
    site, _ = ProjectSite.objects.get_or_create(name="Test Site for Absent Task", defaults={'latitude': 0, 'longitude': 0})

    # Create a test worker
    worker_username = "test_worker_absent_task"
    worker, created = CustomUser.objects.get_or_create(username=worker_username, defaults={'role': 'WORKER'})
    if created:
        worker.set_password("password")
        worker.save()
    
    worker.assigned_site = site
    worker.save()

    # Ensure no attendance for today
    today = get_ist_date()
    Attendance.objects.filter(worker=worker, date=today).delete()
    
    # Clear audit logs for attendance to be sure
    # (Optional, but helps verification)
    
    print(f"Running mark_absent command for date {today}...")
    call_command('mark_absent', date=str(today))

    # Verify Attendance Created
    attendance = Attendance.objects.filter(worker=worker, date=today, status='ABSENT').first()
    if attendance:
        print("SUCCESS: Attendance record created with status 'ABSENT'.")
    else:
        print("FAILURE: Attendance record NOT created.")
        return

    # Verify Audit Log
    # Audit log for CREATE action on Attendance model
    # We expect NO log for this specific record creation because bulk_create was used
    # However, audit log might capture other things or existing logs.
    # We check if there is a CREATE log for this specific record ID.
    
    audit_entry = AuditLog.objects.filter(
        model_name='Attendance',
        record_id=str(attendance.id),
        action='CREATE'
    ).first()

    if audit_entry:
        print(f"FAILURE: Audit log entry found! ID: {audit_entry.id}")
    else:
        print("SUCCESS: No audit log entry found for this creation.")

    # Cleanup
    print("Cleaning up...")
    attendance.delete()
    worker.delete()
    site.delete()  # Only if created for this test, but might be shared. keeping it simple.
    # actually better not to delete site if it was existing.
    if _ : # if site was created
        site.delete()

if __name__ == "__main__":
    run_test()
