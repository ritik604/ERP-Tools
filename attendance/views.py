from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Attendance
from projects.models import ProjectSite
from django.utils import timezone
from geopy.distance import geodesic
from django.contrib import messages

@login_required
def mark_attendance(request):
    user = request.user
    if user.role not in ['WORKER', 'SUPERVISOR']:
        # Admin logic? For now redirect to dashboard
        return redirect('dashboard')
    
    assigned_site = user.assigned_site
    if not assigned_site:
        return render(request, 'attendance/error.html', {'message': "You are not assigned to any site."})

    today = timezone.now().date()
    already_checked_in = Attendance.objects.filter(worker=user, date=today).exists()

    if request.method == 'POST':
        if already_checked_in:
            return redirect('attendance:attendance_list')

        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        
        if not lat or not lon:
             return render(request, 'attendance/mark_attendance.html', {'error': "Location access required to mark attendance.", 'site': assigned_site})

        worker_loc = (float(lat), float(lon))
        site_loc = (assigned_site.latitude, assigned_site.longitude)
        distance = geodesic(worker_loc, site_loc).km
        
        verified = distance <= 1.0
        
        Attendance.objects.create(
            worker=user,
            site=assigned_site,
            date=today,
            check_in_time=timezone.now(),
            status='PRESENT',
            latitude=lat,
            longitude=lon,
            verified=verified
        )
        return redirect('attendance:attendance_list')

    return render(request, 'attendance/mark_attendance.html', {'site': assigned_site, 'already_checked_in': already_checked_in})

from django.db.models import Q
import xlwt
from django.http import HttpResponse

from django.core.paginator import Paginator
from django.template.loader import render_to_string
import csv

@login_required
def attendance_list(request):
    user = request.user
    queryset = Attendance.objects.select_related('worker', 'site').all()

    # Base Role Filtering
    if user.role == 'SUPERVISOR':
        if user.assigned_site:
            queryset = queryset.filter(Q(worker=user) | Q(site=user.assigned_site))
        else:
            queryset = queryset.filter(worker=user)
    elif user.role == 'WORKER':
        queryset = queryset.filter(worker=user)
    
    # Apply UI Filters
    name_query = request.GET.get('name')
    site_id = request.GET.get('site')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if name_query:
        queryset = queryset.filter(
            Q(worker__username__icontains=name_query) | 
            Q(worker__first_name__icontains=name_query) |
            Q(worker__last_name__icontains=name_query)
        )
    
    if site_id:
        queryset = queryset.filter(site__id=site_id)
    
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
        
    queryset = queryset.order_by('-date', '-check_in_time')

    # Metrics (based on filtered queryset before pagination)
    total_count = queryset.count()
    if total_count > 0:
        present_count = queryset.filter(status='PRESENT').count()
        attendance_percentage = (present_count / total_count) * 100
    else:
        attendance_percentage = 0
        
    unique_employees = queryset.values('worker').distinct().count()

    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'attendance_percentage': round(attendance_percentage, 1),
        'unique_employees': unique_employees,
        'total_count': total_count,
        'sites': ProjectSite.objects.all() if user.role == 'ADMIN' else [user.assigned_site] if user.assigned_site else [],
        
        # Keep filter values for non-AJAX requests (not strictly needed with AJAX approach but good for initial load)
        'filter_name': name_query or '',
        'filter_site': site_id or '',
        'filter_start': start_date or '',
        'filter_end': end_date or '',
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('attendance/attendance_table_partial.html', context, request=request)
        return HttpResponse(html)

    return render(request, 'attendance/history.html', context)

@login_required
def export_attendance_csv(request):
    """Dedicated view for exporting attendance data to CSV."""
    user = request.user
    queryset = Attendance.objects.select_related('worker', 'site').all()

    # Base Role Filtering
    if user.role == 'SUPERVISOR':
        if user.assigned_site:
            queryset = queryset.filter(Q(worker=user) | Q(site=user.assigned_site))
        else:
            queryset = queryset.filter(worker=user)
    elif user.role == 'WORKER':
        queryset = queryset.filter(worker=user)
    
    # Apply UI Filters
    name_query = request.GET.get('name')
    site_id = request.GET.get('site')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if name_query:
        queryset = queryset.filter(
            Q(worker__username__icontains=name_query) | 
            Q(worker__first_name__icontains=name_query) |
            Q(worker__last_name__icontains=name_query)
        )
    
    if site_id:
        queryset = queryset.filter(site__id=site_id)
    
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
        
    queryset = queryset.order_by('-date', '-check_in_time')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Name', 'Site', 'Check In', 'Verified', 'Status'])
    
    for record in queryset:
        writer.writerow([
            record.date.strftime("%B %d, %Y") if record.date else "-",
            record.worker.get_full_name() or record.worker.username,
            record.site.name if record.site else "-",
            record.check_in_time.strftime("%I:%M %p") if record.check_in_time else "-",
            "Yes" if record.verified else "No",
            record.get_status_display()
        ])
        
    return response

@login_required
def attendance_update(request, pk):
    if request.user.role not in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    record = get_object_or_404(Attendance, pk=pk)
    
    # Supervisor can only edit records from their site
    if request.user.role == 'SUPERVISOR':
        if record.site != request.user.assigned_site:
            messages.error(request, "You can only edit attendance for your assigned site.")
            return redirect('attendance:attendance_list')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_verified = request.POST.get('verified') == 'on'
        
        record.status = new_status
        record.verified = new_verified
        record.save()
        
        messages.success(request, f"Attendance record updated for {record.worker.username}")
        return redirect('attendance:attendance_list')
    
    return render(request, 'attendance/attendance_form.html', {'record': record})
