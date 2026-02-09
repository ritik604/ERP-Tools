from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import CustomUser
from attendance.models import Attendance, get_ist_date
import datetime

class Command(BaseCommand):
    help = 'Marks active employees with assigned sites as ABSENT if they have not marked attendance for the day.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date in YYYY-MM-DD format to mark attendance for. Defaults to today (IST).'
        )

    def handle(self, *args, **options):
        # 1. Determine target date
        date_str = options['date']
        if date_str:
            try:
                target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Please use YYYY-MM-DD.'))
                return
        else:
            # Default to today in local timezone (IST as per settings)
            target_date = get_ist_date()

        self.stdout.write(f"Running mark_absent for date: {target_date}")

        # 2. Filter target users
        # Active WORKER or SUPERVISOR with an assigned site
        # Users without assigned_site cannot have attendance created as 'site' is mandatory
        target_users = CustomUser.objects.filter(
            is_active=True,
            role__in=['WORKER', 'SUPERVISOR'],
            assigned_site__isnull=False
        )

        total_target_users = target_users.count()
        self.stdout.write(f"Found {total_target_users} active workers/supervisors with assigned sites.")

        if total_target_users == 0:
            self.stdout.write(self.style.WARNING("No eligible employees found."))
            return

        # 3. Identify who already has attendance
        existing_attendance_worker_ids = Attendance.objects.filter(
            date=target_date,
            worker__in=target_users
        ).values_list('worker_id', flat=True)

        # 4. Filter users who need 'ABSENT' record
        users_to_mark = target_users.exclude(id__in=existing_attendance_worker_ids)
        
        count_to_mark = users_to_mark.count()
        self.stdout.write(f"Employees with attendance: {existing_attendance_worker_ids.count()}")
        self.stdout.write(f"Employees to mark ABSENT: {count_to_mark}")

        if count_to_mark == 0:
            self.stdout.write(self.style.SUCCESS("All eligible employees have attendance marked for this date. No action needed."))
            return

        # 5. Create Attendance objects
        attendance_objects = []
        for user in users_to_mark:
            attendance_objects.append(
                Attendance(
                    worker=user,
                    site=user.assigned_site,
                    date=target_date,
                    status='ABSENT',
                    verified=False,
                    check_in_time=None,
                    latitude=None,
                    longitude=None
                )
            )

        # 6. Bulk Create (Bypasses signals -> No Audit Log)
        Attendance.objects.bulk_create(attendance_objects)

        self.stdout.write(self.style.SUCCESS(f"Successfully marked {count_to_mark} employees as ABSENT for {target_date}."))
