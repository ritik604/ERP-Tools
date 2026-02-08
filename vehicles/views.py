from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Vehicle
from .forms import VehicleForm
from projects.models import ProjectSite

@login_required
def vehicle_list(request):
    if request.user.role not in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    vehicles = Vehicle.objects.all().select_related('assigned_site')
    
    # Filtering
    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')
    site_filter = request.GET.get('site', '')
    
    if search_query:
        vehicles = vehicles.filter(
            Q(name__icontains=search_query) |
            Q(plate_number__icontains=search_query) |
            Q(vehicle_id__icontains=search_query)
        )
    
    if type_filter:
        vehicles = vehicles.filter(vehicle_type=type_filter)
    
    if site_filter:
        vehicles = vehicles.filter(assigned_site_id=site_filter)
    
    sites = ProjectSite.objects.all()
    
    context = {
        'vehicles': vehicles,
        'sites': sites,
        'search_query': search_query,
        'type_filter': type_filter,
        'site_filter': site_filter,
        'is_admin': request.user.role == 'ADMIN',
        'vehicle_types': Vehicle.VEHICLE_TYPE_CHOICES
    }
    return render(request, 'vehicles/vehicle_list.html', context)

@login_required
def vehicle_create(request):
    if request.user.role != 'ADMIN':
        messages.error(request, "Only Admins can add vehicles.")
        return redirect('vehicle_list')
    
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            messages.success(request, f'Vehicle {vehicle.name} added successfully!')
            return redirect('vehicle_list')
    else:
        form = VehicleForm()
    
    return render(request, 'vehicles/vehicle_form.html', {'form': form, 'title': 'Add New Vehicle'})

@login_required
def vehicle_detail(request, pk):
    if request.user.role not in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    vehicle = get_object_or_404(Vehicle, pk=pk)
    return render(request, 'vehicles/vehicle_detail.html', {
        'vehicle': vehicle, 
        'is_admin': request.user.role == 'ADMIN'
    })

@login_required
def vehicle_update(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, "Only Admins can update vehicle details.")
        return redirect('vehicle_list')
    
    vehicle = get_object_or_404(Vehicle, pk=pk)
    
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f'Vehicle {vehicle.name} updated successfully!')
            return redirect('vehicle_detail', pk=pk)
    else:
        form = VehicleForm(instance=vehicle)
    
    return render(request, 'vehicles/vehicle_edit.html', {'form': form, 'vehicle': vehicle})

@login_required
def vehicle_delete(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, "Only Admins can delete vehicles.")
        return redirect('vehicle_list')
    
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        name = vehicle.name
        vehicle.delete()
        messages.success(request, f'Vehicle {name} deleted successfully!')
        return redirect('vehicle_list')
    
    return render(request, 'vehicles/vehicle_confirm_delete.html', {'vehicle': vehicle})
