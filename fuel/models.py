from django.db import models, transaction
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from projects.models import ProjectSite
from core.utils import get_ist_now, get_ist_date


class FuelRecord(models.Model):
    """Model to track fuel expenses across projects."""
    
    FUEL_TYPE_CHOICES = (
        ('DIESEL', 'Diesel'),
        ('PETROL', 'Petrol'),
        ('CNG', 'CNG'),
    )
    
    record_id = models.CharField(max_length=20, unique=True, editable=False)
    project = models.ForeignKey(
        ProjectSite, 
        on_delete=models.CASCADE, 
        related_name='fuel_records'
    )
    date = models.DateField(default=get_ist_date)
    fuel_type = models.CharField(
        max_length=20, 
        choices=FUEL_TYPE_CHOICES, 
        default='DIESEL'
    )
    quantity_liters = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Quantity in liters"
    )
    price_per_liter = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Price per liter in INR",
        null=True,
        blank=True
    )
    total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Total amount paid",
        default=0
    )
    receipt = models.ImageField(upload_to='fuel_receipts/', blank=True, null=True)  # Legacy field
    vehicle = models.ForeignKey(
        'vehicles.Vehicle', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='fuel_records',
        help_text="Select vehicle or equipment"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=get_ist_now, editable=False)
    updated_at = models.DateTimeField(default=get_ist_now)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['date']),
            models.Index(fields=['fuel_type']),
        ]
    
    def save(self, *args, **kwargs):
        from decimal import Decimal  # Defensively import to avoid NameError
        
        # Update timestamp manually since we removed auto_now=True
        if self.pk:
            self.updated_at = get_ist_now()

        # Auto-generate record_id
        if not self.record_id:
            with transaction.atomic():
                last_record = FuelRecord.objects.select_for_update().order_by('-id').first()
                if last_record and last_record.id:
                    last_id = int(last_record.id)
                else:
                    last_id = 0
                self.record_id = f"FUEL-{last_id + 1:04d}"
        
        # Calculate rates and costs
        if self.total_cost > 0 and self.quantity_liters > 0:
            # If we have total and quantity, calculate rate
            self.price_per_liter = (Decimal(str(self.total_cost)) / Decimal(str(self.quantity_liters))).quantize(Decimal('0.01'))
        elif self.price_per_liter and self.price_per_liter > 0 and self.quantity_liters > 0:
            # Fallback: calculate total from rate and quantity
            self.total_cost = (self.quantity_liters * self.price_per_liter).quantize(Decimal('0.01'))
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.record_id} - {self.project.name}"


class FuelRecordImage(models.Model):
    """Model to store multiple images for a fuel record."""
    fuel_record = models.ForeignKey(FuelRecord, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='fuel_receipts/')
    uploaded_at = models.DateTimeField(default=get_ist_now, editable=False)

    def __str__(self):
        return f"Image for {self.fuel_record.record_id}"
