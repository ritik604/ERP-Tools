
import os
import django
import time
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_erp.settings')
django.setup()

from fuel.models import FuelRecord
from vehicles.models import Vehicle
from core.utils import get_ist_now, get_ist_date
from projects.models import ProjectSite

print(f"Current IST Time: {get_ist_now()}")

# Clean up
FuelRecord.objects.all().delete()
Vehicle.objects.all().delete()
ProjectSite.objects.all().delete()

# Create dummy project
project = ProjectSite.objects.create(name="Test Project", budget=1000)

# Test FuelRecord
print("\nTesting FuelRecord...")
fuel = FuelRecord.objects.create(
    project=project,
    quantity_liters=10,
    total_cost=1000
)

print(f"Fuel created at: {fuel.created_at}")
print(f"Fuel updated at: {fuel.updated_at}")
print(f"Fuel date: {fuel.date}")

if fuel.date != get_ist_date():
    print("ERROR: Fuel date is not IST date!")
else:
    print("SUCCESS: Fuel date is IST date.")

initial_updated_at = fuel.updated_at
initial_created_at = fuel.created_at

time.sleep(2)

fuel.notes = "Updated notes"
fuel.save()

fuel.refresh_from_db()
print(f"Fuel updated at after save: {fuel.updated_at}")

if fuel.updated_at > initial_updated_at:
    print("SUCCESS: Fuel updated_at updated correctly.")
else:
    print("ERROR: Fuel updated_at did not update!")

if fuel.created_at != initial_created_at:
    print("ERROR: Fuel created_at changed!")
else:
    print("SUCCESS: Fuel created_at remained same.")

# Test Vehicle
print("\nTesting Vehicle...")
vehicle = Vehicle.objects.create(
    name="Test Truck",
    plate_number="AB-12-CD-3456"
)

print(f"Vehicle created at: {vehicle.created_at}")
print(f"Vehicle updated at: {vehicle.updated_at}")

initial_vehicle_updated = vehicle.updated_at
time.sleep(2)

vehicle.status = 'MAINTENANCE'
vehicle.save()
vehicle.refresh_from_db()

print(f"Vehicle updated at after save: {vehicle.updated_at}")

if vehicle.updated_at > initial_vehicle_updated:
    print("SUCCESS: Vehicle updated_at updated correctly.")
else:
    print("ERROR: Vehicle updated_at did not update!")

