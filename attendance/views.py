from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Attendance, get_ist_date, get_ist_now
from projects.models import ProjectSite
from django.utils import timezone
from geopy.distance import geodesic
from django.contrib import messages

@login_required
def mark_attendance(request):
    user = request.user
    if user.role not in ['BASIC', 'ELEVATED']:
        # Admin logic? For now redirect to dashboard
        return redirect('dashboard')
    
    assigned_site = user.assigned_site
    if not assigned_site:
        return render(request, 'attendance/error.html', {'message': "You are not assigned to any site."})

    today = get_ist_date()
    # Check if a record already exists (PRESENT, ABSENT, or LEAVE)
    existing_attendance = Attendance.objects.filter(worker=user, date=today).exists()
    
    if existing_attendance:
        # If any record exists, they are blocked from self-service check-in
        return render(request, 'attendance/mark_attendance.html', {
            'site': assigned_site, 
            'already_checked_in': True,
            'message': "Attendance record already exists for today. Please contact an elevated user for any manual updates."
        })

    from django.http import JsonResponse
    
    if request.method == 'POST':
        # If they are blocked (already checked in for today)
        if existing_attendance:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': "Attendance already marked for today."})
            return redirect('attendance:attendance_list')

        # For AJAX, data might be in request.POST or JSON body, but standard POST works for simple forms
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        
        if not lat or not lon:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': "Location access required."})
            return render(request, 'attendance/mark_attendance.html', {'error': "Location access required to mark attendance.", 'site': assigned_site})

        worker_loc = (float(lat), float(lon))
        site_loc = (assigned_site.latitude, assigned_site.longitude)
        distance_km = geodesic(worker_loc, site_loc).km
        distance_meters = distance_km * 1000
        
        # Check against dynamic site radius
        max_radius = assigned_site.site_radius
        if distance_meters > max_radius:
            error_msg = f"You are {distance_meters:.0f} meters away from the site. Attendance can only be marked within {max_radius} meters."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': error_msg})
            return render(request, 'attendance/mark_attendance.html', {
                'error': error_msg,
                'site': assigned_site,
                'distance': round(distance_km, 2),
                'too_far': True
            })
        
        Attendance.objects.create(
            worker=user,
            site=assigned_site,
            date=today,
            check_in_time=get_ist_now(),
            status='PRESENT',
            latitude=lat,
            longitude=lon,
            verified=True
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': "Attendance marked successfully!"})
        return redirect('attendance:attendance_list')

    return render(request, 'attendance/mark_attendance.html', {'site': assigned_site, 'already_checked_in': False})

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
    if user.role == 'ELEVATED':
        if user.assigned_site:
            queryset = queryset.filter(Q(worker=user) | Q(site=user.assigned_site))
        else:
            queryset = queryset.filter(worker=user)
    elif user.role == 'BASIC':
        queryset = queryset.filter(worker=user)
    
    # Apply UI Filters
    name_query = request.GET.get('name')
    site_id = request.GET.get('site')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')

    if start_date is None and end_date is None:
        today_str = get_ist_date().strftime('%Y-%m-%d')
        start_date = today_str
        end_date = today_str

    if name_query:
        queryset = queryset.filter(
            Q(worker__username__icontains=name_query) | 
            Q(worker__first_name__icontains=name_query) |
            Q(worker__last_name__icontains=name_query)
        )
    
    if site_id:
        queryset = queryset.filter(site__id=site_id)
    
    if status:
        queryset = queryset.filter(status=status)
    
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
        'attendance_marked': Attendance.objects.filter(worker=user, date=get_ist_date()).exists(),
        'total_count': total_count,
        'sites': ProjectSite.objects.all() if user.role == 'ADMIN' else [user.assigned_site] if user.assigned_site else [],
        'status_choices': Attendance.STATUS_CHOICES,
        
        # Keep filter values for non-AJAX requests (not strictly needed with AJAX approach but good for initial load)
        'filter_name': name_query or '',
        'filter_site': site_id or '',
        'filter_start': start_date or '',
        'filter_end': end_date or '',
        'filter_status': status or '',
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
    if user.role == 'ELEVATED':
        if user.assigned_site:
            queryset = queryset.filter(Q(worker=user) | Q(site=user.assigned_site))
        else:
            queryset = queryset.filter(worker=user)
    elif user.role == 'BASIC':
        queryset = queryset.filter(worker=user)
    
    # Apply UI Filters
    name_query = request.GET.get('name')
    site_id = request.GET.get('site')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')

    if start_date is None and end_date is None:
        today_str = get_ist_date().strftime('%Y-%m-%d')
        start_date = today_str
        end_date = today_str

    if name_query:
        queryset = queryset.filter(
            Q(worker__username__icontains=name_query) | 
            Q(worker__first_name__icontains=name_query) |
            Q(worker__last_name__icontains=name_query)
        )
    
    if site_id:
        queryset = queryset.filter(site__id=site_id)
        
    if status:
        queryset = queryset.filter(status=status)
    
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
        
    queryset = queryset.order_by('-date', '-check_in_time')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Name', 'Designation', 'Site', 'Check In', 'Verified', 'Status'])
    
    for record in queryset:
        writer.writerow([
            record.date.strftime("%B %d, %Y") if record.date else "-",
            record.worker.get_full_name() or record.worker.username,
            record.worker.designation or "-",
            record.site.name if record.site else "-",
            record.check_in_time.strftime("%I:%M %p") if record.check_in_time else "-",
            "Yes" if record.verified else "No",
            record.get_status_display()
        ])
        
    return response

@login_required
def attendance_update(request, pk):
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    record = get_object_or_404(Attendance, pk=pk)
    
    # Supervisor can only edit records from their site
    if request.user.role == 'ELEVATED':
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
@login_required
def check_automation_status(request):
    """
    Endpoint to check if the attendance automation ran for a specific date.
    Returns a plain text report.
    Usage: /attendance/check-status/?date=2024-03-25
    """
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        return HttpResponse("Unauthorized", status=403)

    date_str = request.GET.get('date')
    if date_str:
        try:
            from datetime import datetime
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return HttpResponse("Invalid date format. Use YYYY-MM-DD", status=400)
    else:
        target_date = get_ist_date()

    from core.models import SystemTaskLog
    import os
    
    # 1. Check Database
    try:
        db_record = SystemTaskLog.objects.filter(task_name='mark_absent', run_date=target_date).first()
        run_time = db_record.completed_at.strftime('%H:%M:%S') if db_record else "N/A"
    except Exception as e:
         return HttpResponse(f"Error checking DB: {str(e)}", status=500)

    # 2. Check Log File
    LOG_DIR = "attendance_logs"
    log_filename = f"attendance_summary_{target_date}.log"
    log_path = os.path.join(LOG_DIR, log_filename)
    file_exists = os.path.exists(log_path)
    
    # Generate Output
    output = []
    output.append(f"STATUS REPORT FOR {target_date}")
    output.append("-" * 30)
    
    if db_record:
        output.append(f"[OK] Database Record Found: Run at {run_time}")
    else:
        output.append("[MISSING] Database Record MISSING")
        
    if file_exists:
        output.append(f"[OK] Log File Found: {log_path}")
        try:
            with open(log_path, 'r') as f:
                content = f.readlines()
                # Extract the 3 count lines (usually lines 5, 6, 7 in the log file)
                # But safer to just dump the whole content or search key lines
                relevant_lines = [line.strip() for line in content if ":" in line and ("Total" in line or "Marked" in line or "Absent" in line)]
                for line in relevant_lines:
                    output.append(f"    -> {line}")
        except:
             output.append("    -> (Could not read file content)")
    else:
        output.append(f"[MISSING] Log File MISSING: {log_filename}")
        
    output.append("-" * 30)
    
    if db_record and file_exists:
         output.append("RESULT: Automation ran successfully today.")
    elif db_record:
         output.append("RESULT: DB says it ran, but log file is missing (maybe deleted?).")
    else:
         output.append("RESULT: Automation HAS NOT RUN today yet.")

    return HttpResponse("\n".join(output), content_type="text/plain")
