from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from .models import FuelRecord
from .forms import FuelRecordForm
from projects.models import ProjectSite


from django.core.paginator import Paginator
from django.template.loader import render_to_string
import csv
from django.http import HttpResponse

@login_required
def fuel_list(request):
    """List all fuel records with filtering options."""
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    query = request.GET.get('q')
    project_filter = request.GET.get('project')
    fuel_type_filter = request.GET.get('fuel_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    records = FuelRecord.objects.all().select_related('project', 'vehicle')
    
    if query:
        records = records.filter(
            Q(record_id__icontains=query) | 
            Q(vehicle__name__icontains=query) |
            Q(vehicle__plate_number__icontains=query) |
            Q(project__name__icontains=query)
        )
    
    if project_filter:
        records = records.filter(project_id=project_filter)
    
    if fuel_type_filter:
        records = records.filter(fuel_type=fuel_type_filter)
    
    if date_from:
        records = records.filter(date__gte=date_from)
    
    if date_to:
        records = records.filter(date__lte=date_to)
    
    records = records.order_by('-date', '-created_at').select_related('vehicle', 'project')

    # Metrics (based on filtered queryset before pagination)
    total_count = records.count()
    total_cost_sum = records.aggregate(
        total=Sum('total_cost')
    )['total'] or 0
    
    total_liters_sum = records.aggregate(
        total=Sum('quantity_liters')
    )['total'] or 0
    
    # Pagination
    paginator = Paginator(records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all projects for filter dropdown
    projects = ProjectSite.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'projects': projects,
        'total_cost_sum': total_cost_sum,
        'total_liters_sum': total_liters_sum,
        'total_count': total_count,
        'filter_q': query or '',
        'filter_project': project_filter or '',
        'filter_fuel_type': fuel_type_filter or '',
        'filter_date_from': date_from or '',
        'filter_date_to': date_to or '',
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('fuel/fuel_table_partial.html', context, request=request)
        return HttpResponse(html)

    return render(request, 'fuel/fuel_list.html', context)

@login_required
def export_fuel_csv(request):
    """Dedicated view for exporting fuel records to CSV."""
    if request.user.role != 'ADMIN':
        return HttpResponse("Access Denied", status=403)
    
    query = request.GET.get('q')
    project_filter = request.GET.get('project')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    records = FuelRecord.objects.all().select_related('project', 'vehicle')
    
    if query:
        records = records.filter(
            Q(record_id__icontains=query) | 
            Q(vehicle__name__icontains=query) |
            Q(vehicle__plate_number__icontains=query) |
            Q(project__name__icontains=query)
        )
    
    if project_filter:
        records = records.filter(project_id=project_filter)
    
    if date_from:
        records = records.filter(date__gte=date_from)
    
    if date_to:
        records = records.filter(date__lte=date_to)
    
    records = records.order_by('-date', '-created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fuel_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Record ID', 'Date', 'Project', 'Vehicle', 'Fuel', 'Quantity', 'Cost'])
    
    for record in records:
        writer.writerow([
            record.record_id,
            record.date.strftime("%Y-%m-%d") if record.date else "-",
            record.project.name if record.project else "Global/Unassigned",
            str(record.vehicle) if record.vehicle else "Global/Other",
            record.get_fuel_type_display(),
            record.quantity_liters,
            record.total_cost
        ])
        
    return response


@login_required
def fuel_create(request):
    """Create a new fuel record."""
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = FuelRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save()
            messages.success(request, f'Fuel record "{record.record_id}" created!')
            return redirect('fuel:fuel_list')
    else:
        form = FuelRecordForm()
    
    return render(request, 'fuel/fuel_form.html', {
        'form': form,
        'title': 'Add Fuel Record'
    })


@login_required
def fuel_detail(request, pk):
    """View fuel record details."""
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    record = get_object_or_404(FuelRecord, pk=pk)
    
    return render(request, 'fuel/fuel_detail.html', {
        'record': record
    })


@login_required
def fuel_update(request, pk):
    """Update an existing fuel record."""
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    record = get_object_or_404(FuelRecord, pk=pk)
    
    if request.method == 'POST':
        form = FuelRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, f'Fuel record "{record.record_id}" updated!')
            return redirect('fuel:fuel_list')
    else:
        form = FuelRecordForm(instance=record)
    
    return render(request, 'fuel/fuel_form.html', {
        'form': form,
        'record': record,
        'title': 'Edit Fuel Record'
    })


@login_required
def fuel_delete(request, pk):
    """Delete a fuel record."""
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    record = get_object_or_404(FuelRecord, pk=pk)
    
    if request.method == 'POST':
        record_id = record.record_id
        record.delete()
        messages.success(request, f'Fuel record "{record_id}" deleted!')
        return redirect('fuel:fuel_list')
    
    return render(request, 'fuel/fuel_confirm_delete.html', {
        'record': record
    })
