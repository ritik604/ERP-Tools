from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import CustomUser
from attendance.models import Attendance, get_ist_date
import datetime
import os
import glob

# Directory for logs
LOG_DIR = "attendance_logs"

def cleanup_old_logs():
    """Removes log files older than 7 days."""
    if not os.path.exists(LOG_DIR):
        return
    
    seven_days_ago = get_ist_date() - datetime.timedelta(days=7)
    files = glob.glob(os.path.join(LOG_DIR, "attendance_summary_*.log"))
    
    for file_path in files:
        try:
            # Filename format: attendance_summary_YYYY-MM-DD.log
            filename = os.path.basename(file_path)
            date_str = filename.replace("attendance_summary_", "").replace(".log", "")
            file_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            
            if file_date < seven_days_ago:
                os.remove(file_path)
        except (ValueError, OSError):
            continue

def run_mark_attendance_logic(target_date=None):
    """
    Core logic to mark employees absent, generate a report, and log it to a daily file.
    Designed to run safely in a background thread.
    """
    from django.db import close_old_connections, transaction
    
    # Close old connections to ensure thread safety
    close_old_connections()

    if not target_date:
        target_date = get_ist_date()

    with transaction.atomic():
        # 1. Filter target users
        target_users = CustomUser.objects.filter(
            is_active=True,
            role__in=['BASIC', 'ELEVATED'],
            assigned_site__isnull=False,
            date_joined__lte=target_date
        )
    total_users = target_users.count()

    # 3. Identify missing attendance
    existing_ids = Attendance.objects.filter(
        date=target_date,
        worker__in=target_users
    ).values_list('worker_id', flat=True)

    users_to_mark = target_users.exclude(id__in=existing_ids)
    count_to_mark = users_to_mark.count()

    # 4. Create Absent records
    if count_to_mark > 0:
        attendance_objects = []
        for user in users_to_mark:
            attendance_objects.append(
                Attendance(
                    worker=user,
                    site=user.assigned_site,
                    date=target_date,
                    status='ABSENT',
                    verified=False
                )
            )
        Attendance.objects.bulk_create(attendance_objects)

    # 5. Generate Summary
    final_attendance = Attendance.objects.filter(date=target_date, worker__in=target_users)
    present_count = final_attendance.filter(status='PRESENT').count()
    absent_count = final_attendance.filter(status='ABSENT').count()
    
    summary = (
        f"ATTENDANCE SUMMARY FOR {target_date}\n"
        f"{'='*40}\n"
        f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Total Eligible Basic/Elevated: {total_users}\n"
        f"Already Marked Present: {present_count}\n"
        f"Auto-Marked Absent:    {count_to_mark}\n"
        f"Final Absent Count:    {absent_count}\n"
        f"{'='*40}\n"
    )

    # 6. Write to daily log file
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    log_filename = os.path.join(LOG_DIR, f"attendance_summary_{target_date}.log")
    with open(log_filename, 'w') as f:
        f.write(summary)

    # 7. Cleanup tasks
    cleanup_old_logs()

    return count_to_mark, summary

class Command(BaseCommand):
    help = 'Marks missing attendance as ABSENT and logs results to a daily text file.'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='YYYY-MM-DD')

    def handle(self, *args, **options):
        date_str = options['date']
        target_date = None
        if date_str:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

        count, msg = run_mark_attendance_logic(target_date)
        self.stdout.write(msg)
