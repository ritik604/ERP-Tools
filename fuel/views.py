from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from core.utils import get_ist_date
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
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    query = request.GET.get('q')
    project_filter = request.GET.get('project')
    fuel_type_filter = request.GET.get('fuel_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from is None and date_to is None:
        today_str = get_ist_date().strftime('%Y-%m-%d')
        date_from = today_str
        date_to = today_str
    
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
        'is_admin': request.user.role in ['ADMIN', 'ELEVATED'],
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('fuel/fuel_table_partial.html', context, request=request)
        return HttpResponse(html)

    return render(request, 'fuel/fuel_list.html', context)

@login_required
def export_fuel_csv(request):
    """Dedicated view for exporting fuel records to CSV."""
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        return HttpResponse("Access Denied", status=403)
    
    query = request.GET.get('q')
    project_filter = request.GET.get('project')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from is None and date_to is None:
        today_str = get_ist_date().strftime('%Y-%m-%d')
        date_from = today_str
        date_to = today_str
    
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
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    if request.method == 'POST':
        form = FuelRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save()
            
            # Handle multiple image uploads
            from .models import FuelRecordImage
            files = request.FILES.getlist('images')
            for f in files:
                FuelRecordImage.objects.create(fuel_record=record, image=f)
            
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
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    record = get_object_or_404(FuelRecord, pk=pk)
    
    return render(request, 'fuel/fuel_detail.html', {
        'record': record,
        'is_admin': request.user.role in ['ADMIN', 'ELEVATED'],
    })


@login_required
def fuel_update(request, pk):
    """Update an existing fuel record."""
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    record = get_object_or_404(FuelRecord, pk=pk)
    
    if request.method == 'POST':
        form = FuelRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            from .models import FuelRecordImage
            
            # Capture existing images before any changes
            existing_images = list(record.images.all())
            existing_image_names = [img.image.name.split('/')[-1] for img in existing_images]
            
            form.save()
            
            # Track deleted images
            deleted_image_names = []
            delete_images = request.POST.get('delete_images', '')
            if delete_images:
                image_ids = [int(id) for id in delete_images.split(',') if id.strip()]
                for image_id in image_ids:
                    try:
                        image = FuelRecordImage.objects.get(pk=image_id, fuel_record=record)
                        deleted_image_names.append(image.image.name.split('/')[-1])
                        image.image.delete()  # Delete the file
                        image.delete()  # Delete the record
                    except FuelRecordImage.DoesNotExist:
                        pass
            
            # Track new images
            new_image_names = []
            files = request.FILES.getlist('images')
            for f in files:
                new_img = FuelRecordImage.objects.create(fuel_record=record, image=f)
                new_image_names.append(new_img.image.name.split('/')[-1])

            # Update existing audit log entry with image changes if any occurred
            if deleted_image_names or new_image_names:
                from audit.models import AuditLog
                from django.utils import timezone
                from datetime import timedelta
                
                # Calculate remaining images
                remaining_image_names = [name for name in existing_image_names if name not in deleted_image_names]
                remaining_image_names.extend(new_image_names)
                
                # Build single 'images' change entry with pipe-delimited names
                image_changes = {
                    'images': {
                        'old': ' | '.join(existing_image_names) if existing_image_names else 'None',
                        'new': ' | '.join(remaining_image_names) if remaining_image_names else 'None'
                    }
                }
                
                # Find and update the most recent audit entry for this record (created within last 5 seconds)
                recent_time = timezone.now() - timedelta(seconds=5)
                existing_audit = AuditLog.objects.filter(
                    module='fuel',
                    model_name='FuelRecord',
                    record_id=str(record.pk),
                    action='UPDATE',
                    timestamp__gte=recent_time
                ).order_by('-timestamp').first()
                
                if existing_audit:
                    # Merge image changes into existing audit entry
                    existing_audit.changes.update(image_changes)
                    existing_audit.save()
                else:
                    # No recent audit entry found, create one
                    from audit.middleware import get_current_ip
                    AuditLog.objects.create(
                        module='fuel',
                        model_name='FuelRecord',
                        record_id=str(record.pk),
                        record_repr=str(record)[:255],
                        action='UPDATE',
                        user=request.user,
                        changes=image_changes,
                        ip_address=get_current_ip()
                    )
            
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
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    record = get_object_or_404(FuelRecord, pk=pk)
    
    if request.method == 'POST':
        record_id = record.record_id
        record.delete()
        messages.success(request, f'Fuel record "{record_id}" deleted!')
        return redirect('fuel:fuel_list')
    
    return render(request, 'fuel/fuel_confirm_delete.html', {
        'record': record
    })
