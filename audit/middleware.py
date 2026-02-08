"""
Middleware to capture current user and IP address for audit logging.
Uses thread-local storage to make user context available in signal handlers.
"""
from threading import local

_thread_locals = local()


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
        
        response = self.get_response(request)
        
        # Clean up thread-local storage after request
        _thread_locals.user = None
        _thread_locals.ip_address = None
        
        return response

    def get_client_ip(self, request):
        """Extract client IP address from request headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP if there's a chain of proxies
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
