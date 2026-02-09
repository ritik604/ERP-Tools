"""
Middleware to capture current user and IP address for audit logging.
Uses thread-local storage to make user context available in signal handlers.
"""
import threading
import logging
from threading import local
from django.utils import timezone
from core.utils import get_ist_now, get_ist_date
from core.models import SystemTaskLog
from attendance.management.commands.mark_attendance import run_mark_attendance_logic

_thread_locals = local()
logger = logging.getLogger(__name__)

# Memory cache to avoid hitting the DB on every single request
# Stores {task_name: last_run_date}
_task_run_cache = {}

def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, 'user', None)


def get_current_ip():
    """Get the current IP address from thread-local storage."""
    return getattr(_thread_locals, 'ip_address', None)


class AuditMiddleware:
    """
    Middleware that captures the current request's user and IP address
    and stores them in thread-local storage for use by audit signals.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store user in thread-local storage (only if authenticated)
        _thread_locals.user = request.user if request.user.is_authenticated else None
        _thread_locals.ip_address = self.get_client_ip(request)
        
        # Self-Triggering Periodic Tasks (Run on first hit after target time)
        # Optimized to avoid redundant DB checks
        self.check_periodic_tasks()
        
        response = self.get_response(request)
        
        # Clean up thread-local storage after request
        _thread_locals.user = None
        _thread_locals.ip_address = None
        
        return response

    def check_periodic_tasks(self):
        """Checks and runs daily tasks if the time window is met."""
        now = get_ist_now()
        today = get_ist_date()

        # Task: Mark Absentees (Run after 1:00 PM / 13:00)
        # 1. Quick hour check
        if now.hour >= 13:
            # 2. Memory cache check to avoid DB hit on 99.9% of requests
            if _task_run_cache.get('mark_absent') == today:
                return

            try:
                # 3. DB check (Only happens once per process per day)
                log, created = SystemTaskLog.objects.get_or_create(
                    task_name='mark_absent',
                    run_date=today
                )
                
                # Update memory cache regardless of created status
                # This stops this process from checking the DB again today
                _task_run_cache['mark_absent'] = today

                if created:
                    # 4. Run the heavy work in a background thread
                    # Daemon=True ensures it doesn't block server shutdown
                    thread = threading.Thread(
                        target=run_mark_attendance_logic,
                        args=(today,),
                        daemon=True
                    )
                    thread.start()
                    logger.info(f"Launched attendance automation in background thread for {today}")
            except Exception as e:
                # Never block the request
                logger.error(f"Failed to check/trigger attendance logic: {e}")

    def get_client_ip(self, request):
        """Extract client IP address from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP if there's a chain of proxies
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
