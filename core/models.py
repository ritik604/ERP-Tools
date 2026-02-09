from django.db import models
from core.utils import get_ist_now

class SystemTaskLog(models.Model):
    task_name = models.CharField(max_length=100)
    run_date = models.DateField()
    completed_at = models.DateTimeField(default=get_ist_now, editable=False)

    class Meta:
        unique_together = ('task_name', 'run_date')

    def __str__(self):
        return f"{self.task_name} - {self.run_date}"
