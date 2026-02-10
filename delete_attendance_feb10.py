import os
import django
from datetime import date

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_erp.settings')
django.setup()

from attendance.models import Attendance

def delete_attendance_records(target_date):
    """
    Deletes all attendance records for a specific date.
    """
    print(f"Searching for attendance records on {target_date}...")
    
    # Filter records for the target date
    records = Attendance.objects.filter(date=target_date)
    count = records.count()
    
    if count == 0:
        print(f"No attendance records found for {target_date}.")
        return

    print(f"Found {count} records. Deleting...")
    
    # Perform deletion
    deleted_count, _ = records.delete()
    
    print(f"Successfully deleted {deleted_count} attendance records for {target_date}.")

if __name__ == "__main__":
    # Target date: February 10, 2026
    TARGET_DATE = date(2026, 2, 10)
    
    # Confirmation prompt (optional for server scripts, but good practice)
    confirm = input(f"Are you sure you want to delete all attendance records for {TARGET_DATE}? (y/n): ")
    if confirm.lower() == 'y':
        delete_attendance_records(TARGET_DATE)
    else:
        print("Operation cancelled.")
