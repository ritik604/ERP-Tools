from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = 'Audit Trail'
    
    def ready(self):
        # Import signals to register them
        import audit.signals  # noqa
