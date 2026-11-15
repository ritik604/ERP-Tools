from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Attendance, get_ist_date, get_ist_now
from projects.models import ProjectSite
from django.utils import timezone
from geopy.distance import geodesic
from django.contrib import messages

from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.template.loader import render_to_string
import csv

@login_required
def attendance_list(request):
    user = request.user

    # Handle Check-In Submission (via AJAX or standard POST)
    if request.method == 'POST':
        today = get_ist_date()
        assigned_site = user.assigned_site
        if not assigned_site and user.role == 'ADMIN':
            assigned_site = ProjectSite.objects.filter(status='ACTIVE').first()

        existing_attendance = Attendance.objects.filter(worker=user, date=today).exists()
        if existing_attendance:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': "Attendance already marked for today."})
            messages.warning(request, "Attendance already marked for today.")
            return redirect('attendance:attendance_list')

        if not assigned_site:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': "You are not assigned to any project site."})
            messages.error(request, "You are not assigned to any project site.")
            return redirect('attendance:attendance_list')

        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        
        if not lat or not lon:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': "Location access required to mark attendance."})
            messages.error(request, "Location access required to mark attendance.")
            return redirect('attendance:attendance_list')

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
            messages.error(request, error_msg)
            return redirect('attendance:attendance_list')

        # Facial Recognition Verification
        face_embedding_raw = request.POST.get('face_embedding')
        liveness_verified = request.POST.get('liveness_verified') == 'true'
        photo_data = request.POST.get('photo')
        request_override = request.POST.get('request_override') == 'true'

        face_verified = False
        face_distance = None
        verification_mode = 'GPS_ONLY'
        is_verified = True

        if user.is_face_enrolled:
            if request_override:
                face_verified = False
                verification_mode = 'SUPERVISOR_OVERRIDE'
                is_verified = False
            else:
                if not face_embedding_raw:
                    msg = "Live facial scan required for check-in."
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': msg})
                    messages.error(request, msg)
                    return redirect('attendance:attendance_list')

                if not liveness_verified:
                    msg = "Liveness verification required. Please look into the camera and blink naturally to prove you are a live person."
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': msg})
                    messages.error(request, msg)
                    return redirect('attendance:attendance_list')

                import json
                from attendance.utils import verify_face_match

                try:
                    if isinstance(face_embedding_raw, str):
                        live_embedding = json.loads(face_embedding_raw)
                    else:
                        live_embedding = face_embedding_raw
                except Exception:
                    live_embedding = None

                is_match, dist, match_msg = verify_face_match(live_embedding, user.face_embedding)
                face_distance = round(dist, 3)

                if not is_match:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'face_mismatch': True,
                            'distance': face_distance,
                            'message': f"Face verification failed (Match Score: {dist:.2f}, Threshold: 0.55). Ensure face is unobstructed and well-lit."
                        })
                    messages.error(request, f"Face mismatch ({dist:.2f}). Please try again.")
                    return redirect('attendance:attendance_list')

                face_verified = True
                verification_mode = 'GPS_AND_FACE'
                is_verified = True
        else:
            # Un-enrolled workers: fallback to GPS only
            verification_mode = 'GPS_ONLY'
            is_verified = True
            face_verified = False

        # Process check-in audit snapshot
        check_in_photo_file = None
        if photo_data and isinstance(photo_data, str) and photo_data.startswith('data:image'):
            try:
                import base64
                from io import BytesIO
                from PIL import Image
                from django.core.files.base import ContentFile

                header, encoded = photo_data.split(',', 1)
                img_bytes = base64.b64decode(encoded)
                img = Image.open(BytesIO(img_bytes))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.thumbnail((320, 240), Image.LANCZOS)
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=50, optimize=True)
                buffer.seek(0)
                filename = f"checkin_{user.pk}_{today.strftime('%Y%m%d')}.jpg"
                check_in_photo_file = ContentFile(buffer.read(), name=filename)
            except Exception:
                pass

        Attendance.objects.create(
            worker=user,
            site=assigned_site,
            date=today,
            check_in_time=get_ist_now(),
            status='PRESENT',
            latitude=lat,
            longitude=lon,
            verified=is_verified,
            face_verified=face_verified,
            face_distance=face_distance,
            liveness_verified=liveness_verified,
            check_in_photo=check_in_photo_file,
            verification_mode=verification_mode
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            success_msg = "Attendance marked successfully with GPS & Face Verification!" if face_verified else "Attendance recorded successfully!"
            return JsonResponse({'success': True, 'message': success_msg})
        messages.success(request, "Attendance marked successfully!")
        return redirect('attendance:attendance_list')

    # GET Request: Display Attendance Records and Check-In Modal
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

    active_site = user.assigned_site
    if not active_site and user.role == 'ADMIN':
        active_site = ProjectSite.objects.filter(status='ACTIVE').first()

    context = {
        'page_obj': page_obj,
        'active_site': active_site,
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

# Backward-compatibility alias
mark_attendance = attendance_list

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
    writer.writerow(['Date', 'Name', 'Designation', 'Site', 'Check In', 'Verified', 'Verification Mode', 'Face Match Score', 'Status'])
    
    for record in queryset:
        writer.writerow([
            record.date.strftime("%B %d, %Y") if record.date else "-",
            record.worker.get_full_name() or record.worker.username,
            record.worker.designation or "-",
            record.site.name if record.site else "-",
            record.check_in_time.strftime("%I:%M %p") if record.check_in_time else "-",
            "Yes" if record.verified else "No",
            record.get_verification_mode_display(),
            f"{record.face_distance:.2f}" if record.face_distance is not None else "-",
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
    from django.conf import settings
    LOG_DIR = os.path.join(settings.BASE_DIR, "attendance_logs")
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
        output.append(f"[OK] Log File Found: {log_filename}")
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
