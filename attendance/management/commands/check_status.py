from django.core.management.base import BaseCommand
from core.models import SystemTaskLog
from core.utils import get_ist_date
import os

LOG_DIR = "attendance_logs"

class Command(BaseCommand):
    help = 'Checks if the daily attendance automation has run today.'

    def handle(self, *args, **options):
        today = get_ist_date()
        
        # 1. Check Database
        db_record = SystemTaskLog.objects.filter(task_name='mark_absent', run_date=today).first()
        
        # 2. Check Log File
        log_filename = os.path.join(LOG_DIR, f"attendance_summary_{today}.log")
        file_exists = os.path.exists(log_filename)
        
        self.stdout.write(f"\nSTATUS REPORT FOR {today}")
        self.stdout.write("-" * 30)
        
        if db_record:
            self.stdout.write(self.style.SUCCESS(f"[OK] Database Record Found: Run at {db_record.completed_at.strftime('%H:%M:%S')}"))
        else:
            self.stdout.write(self.style.ERROR("[MISSING] Database Record MISSING"))
            
        if file_exists:
            self.stdout.write(self.style.SUCCESS(f"[OK] Log File Found: {log_filename}"))
            # Optional: Print content preview
            with open(log_filename, 'r') as f:
                content = f.read().split('\n')[5:8] # Just the counts
                for line in content:
                    self.stdout.write(f"    -> {line}")
        else:
            self.stdout.write(self.style.ERROR(f"[MISSING] Log File MISSING: {log_filename}"))
            
        self.stdout.write("-" * 30)
        
        if db_record and file_exists:
             self.stdout.write(self.style.SUCCESS("RESULT: Automation ran successfully today."))
        elif db_record:
             self.stdout.write(self.style.WARNING("RESULT: DB says it ran, but log file is missing (maybe deleted?)."))
        else:
             self.stdout.write(self.style.ERROR("RESULT: Automation HAS NOT RUN today yet."))
