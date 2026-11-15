from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import CustomUser
from projects.models import ProjectSite
from attendance.models import Attendance
from core.utils import get_ist_date
from django.db import IntegrityError
from django.db.models import Sum, Q
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserUpdateForm
import csv

@login_required
def home_redirect(request):
    if request.user.role in ['BASIC', 'ELEVATED']:
        return redirect('attendance:attendance_list')
    # ADMIN goes to projects
    return redirect('projects:project_list')

@login_required
def dashboard_view(request):
    user = request.user
    context = {}
    
    today = get_ist_date()
    
    if user.role == 'ADMIN':
        # Redirect admin users to the new project-based dashboard
        return redirect('projects:project_list')
    elif user.role == 'ELEVATED':
        context['title'] = "Elevated Dashboard"
        # Assuming elevated user is assigned to a site or manages basic employees based on some logic
        # For now simply count basic employees
        context['assigned_workers'] = CustomUser.objects.filter(role='BASIC').count()
        
        # Check elevated user's own attendance
        context['attendance_marked'] = Attendance.objects.filter(worker=user, date=today).exists()
        
    elif user.role == 'BASIC':
        context['title'] = "Basic Dashboard"
        last_attendance = Attendance.objects.filter(worker=user).order_by('-check_in_time').first()
        context['last_checkin'] = last_attendance.check_in_time if last_attendance else None
        
        # Check current day attendance
        context['attendance_marked'] = Attendance.objects.filter(worker=user, date=today).exists()
        
        # Ensure last_login is fresh from the user object
        context['last_login'] = user.last_login
    
    return render(request, 'users/dashboard.html', context)


@login_required
def register(request):
    if request.user.role == 'BASIC':
        messages.error(request, "You are not authorized to create users.")
        return redirect('home')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request_user=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Elevated strict permission check
            if request.user.role == 'ELEVATED':
                if user.role != 'BASIC':
                    messages.error(request, "Elevated users can only create Basic employees.")
                    return redirect('register')
            
            try:
                user.save()
                username = form.cleaned_data.get('username')
                messages.success(request, f'Account created for {username}!')
                return redirect('employee_list')
            except IntegrityError as e:
                err_str = str(e).lower()
                if 'username' in err_str:
                    form.add_error('username', 'A user with this username already exists.')
                elif 'employee_id' in err_str:
                    form.add_error(None, 'An employee ID conflict occurred. Please submit again.')
                else:
                    form.add_error(None, f'Database constraint error: {str(e)}')
    else:
        form = CustomUserCreationForm(request_user=request.user)
    return render(request, 'users/register.html', {'form': form})

@login_required
def employee_list(request):
    # Allow WORKER, SUPERVISOR, ADMIN
    # if request.user.role not in ['ADMIN', 'SUPERVISOR']:
    #     messages.error(request, "Access Denied.")
    #     return redirect('dashboard')
    
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    if request.user.role == 'ADMIN':
        employees = CustomUser.objects.all().select_related('assigned_site')
    elif request.user.role == 'ELEVATED':
        # Elevated sees only basic employees
        employees = CustomUser.objects.filter(role='BASIC').select_related('assigned_site')

    
    # Initial Load - Get ALL employees
    employees = employees.order_by('employee_id')
    
    # Get all sites for filter dropdown
    sites = ProjectSite.objects.all()

    # Check attendance for popup
    attendance_marked = False
    if request.user.role in ['BASIC', 'ELEVATED']:
        today = get_ist_date()
        attendance_marked = Attendance.objects.filter(worker=request.user, date=today).exists()

    context = {
        'employees': employees, # Pass all employees
        'sites': sites,
        # Pass empty/default filters if needed for UI state, or just let JS handle it
        'is_admin': request.user.role in ['ADMIN', 'ELEVATED'],
        'attendance_marked': attendance_marked,
    }
    
    return render(request, 'users/employee_list.html', context)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'users/employee_table_partial.html', context)
    
    return render(request, 'users/employee_list.html', context)


@login_required
def employee_detail(request, pk):
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    employee = get_object_or_404(CustomUser, pk=pk)
    
    # Elevated can only view basic employees
    if request.user.role == 'ELEVATED' and employee.role != 'BASIC':
        messages.error(request, "Access Denied.")
        return redirect('employee_list')
    
    return render(request, 'users/employee_detail.html', {'employee': employee, 'is_admin': request.user.role in ['ADMIN', 'ELEVATED']})

@login_required
def employee_update(request, pk):
    # Only ADMIN or ELEVATED can update
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Only Admins can update employee details.")
        return redirect('employee_list')
    
    employee = get_object_or_404(CustomUser, pk=pk)

    if not employee.is_active:
        messages.error(request, "Updates are not allowed on deactivated profiles. Please activate the profile first.")
        return redirect('employee_detail', pk=pk)

    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=employee, request_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Employee {employee.username} updated successfully!')
            return redirect('employee_detail', pk=pk)
    else:
        form = CustomUserUpdateForm(instance=employee, request_user=request.user)
    
    return render(request, 'users/employee_edit.html', {'form': form, 'employee': employee})


@login_required
def toggle_employee_status(request, pk):
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Only Admins can perform this action.")
        return redirect('employee_list')
    
    employee = get_object_or_404(CustomUser, pk=pk)
    employee.is_active = not employee.is_active
    employee.save(update_fields=['is_active'])
    
    status = "activated" if employee.is_active else "deactivated"
    messages.success(request, f'Employee {employee.username} has been {status}.')
    return redirect('employee_detail', pk=pk)


@login_required
def export_employees_csv(request):
    """Export filtered employee list to CSV."""
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Access Denied.")
        return redirect('home')
    
    if request.user.role == 'ADMIN':
        employees = CustomUser.objects.all().select_related('assigned_site')
    else:
        employees = CustomUser.objects.filter(role='BASIC').select_related('assigned_site')
    
    # Apply filters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    site_filter = request.GET.get('site', '')
    status_filter = request.GET.get('status', 'active')
    
    if search_query:
        employees = employees.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        )
    
    if role_filter:
        employees = employees.filter(role=role_filter)
    
    if site_filter:
        employees = employees.filter(assigned_site_id=site_filter)

    if status_filter == 'active':
        employees = employees.filter(is_active=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)
    
    # Generate CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employees_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Designation', 'Role', 'Assigned Site', 'Salary', 'Mobile', 'Government ID'])
    
    for emp in employees:
        writer.writerow([
            emp.employee_id,
            emp.get_full_name() or emp.username,
            emp.designation or '-',
            emp.get_role_display(),
            emp.assigned_site.name if emp.assigned_site else 'Unassigned',
            str(emp.salary) if emp.salary else '-',
            emp.mobile or '-',
            emp.government_id or '-',
        ])
    
    return response


@login_required
def reset_password(request, pk):
    # Only ADMIN can reset password
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Only Admins can reset passwords.")
        return redirect('employee_detail', pk=pk)
    
    employee = get_object_or_404(CustomUser, pk=pk)
    employee.set_password('worker123')
    employee.save(update_fields=['password'])
    
    messages.success(request, f'Password for {employee.username} has been reset to "worker123" successfully!')
    return redirect('employee_detail', pk=pk)

@login_required
def profile(request):
    return render(request, 'users/profile.html', {'employee': request.user})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/change_password.html', {'form': form})


@login_required
def enroll_face(request, pk):
    """Enroll or update facial recognition descriptor for an employee."""
    employee = get_object_or_404(CustomUser, pk=pk)
    
    if request.user.role not in ['ADMIN', 'ELEVATED'] and request.user.pk != employee.pk:
        messages.error(request, "You do not have permission to enroll this face profile.")
        return redirect('employee_detail', pk=pk)
        
    if request.user.role == 'ELEVATED' and employee.role != 'BASIC':
        messages.error(request, "Elevated users can only enroll Basic employees.")
        return redirect('employee_detail', pk=pk)

    if request.method == 'POST':
        import json
        import base64
        from io import BytesIO
        from PIL import Image
        from django.core.files.base import ContentFile
        from attendance.utils import average_embeddings
        from core.utils import get_ist_now
        from django.http import JsonResponse

        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            samples = data.get('samples')
            single_embedding = data.get('face_embedding')
            photo_data = data.get('photo')  # base64 data URL from webcam snapshot
            
            if samples and isinstance(samples, list):
                final_embedding = average_embeddings(samples)
            elif single_embedding:
                if isinstance(single_embedding, str):
                    try:
                        single_embedding = json.loads(single_embedding)
                    except Exception:
                        single_embedding = None
                final_embedding = single_embedding
            else:
                final_embedding = None

            if not final_embedding or len(final_embedding) != 128:
                return JsonResponse({
                    'success': False, 
                    'message': 'Invalid face descriptor received. Please ensure your face is well lit and clearly visible.'
                }, status=400)

            employee.face_embedding = final_embedding
            employee.is_face_enrolled = True
            employee.face_enrolled_at = get_ist_now()

            # Save profile photo from webcam snapshot
            update_fields = ['face_embedding', 'is_face_enrolled', 'face_enrolled_at']
            if photo_data and isinstance(photo_data, str) and photo_data.startswith('data:image'):
                try:
                    # Strip the data URL header (e.g. "data:image/jpeg;base64,")
                    header, encoded = photo_data.split(',', 1)
                    img_bytes = base64.b64decode(encoded)
                    img = Image.open(BytesIO(img_bytes))
                    # Convert to RGB (drop alpha if PNG) and compress as low-quality JPEG
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    # Resize to small thumbnail (max 200px)
                    img.thumbnail((200, 200), Image.LANCZOS)
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=50, optimize=True)
                    buffer.seek(0)
                    filename = f"profile_{employee.pk}.jpg"
                    # Delete old photo file if exists
                    if employee.profile_photo:
                        try:
                            employee.profile_photo.delete(save=False)
                        except Exception:
                            pass
                    employee.profile_photo.save(filename, ContentFile(buffer.read()), save=False)
                    update_fields.append('profile_photo')
                except Exception as photo_err:
                    # Photo save failed — continue with face enrollment anyway
                    import logging
                    logging.getLogger(__name__).warning(f"Profile photo save failed: {photo_err}")

            employee.save(update_fields=update_fields)

            # Log to Audit trail
            try:
                from audit.models import AuditLog
                from audit.middleware import get_current_ip
                AuditLog.objects.create(
                    module='Users',
                    model_name='CustomUser',
                    record_id=str(employee.pk),
                    record_repr=str(employee),
                    action='UPDATE',
                    user=request.user,
                    changes={'is_face_enrolled': {'old': False, 'new': True}},
                    ip_address=get_current_ip()
                )
            except Exception:
                pass

            return JsonResponse({
                'success': True, 
                'message': f'Face profile enrolled successfully for {employee.get_full_name() or employee.username}!'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Server error: {str(e)}'}, status=500)

    return render(request, 'users/enroll_face.html', {'employee': employee})


@login_required
def delete_face_enrollment(request, pk):
    """Removes the enrolled face vector for an employee to allow re-enrollment."""
    employee = get_object_or_404(CustomUser, pk=pk)
    
    if request.user.role not in ['ADMIN', 'ELEVATED']:
        messages.error(request, "Only Admins or Supervisors can delete face enrollments.")
        return redirect('employee_detail', pk=pk)

    employee.face_embedding = None
    employee.is_face_enrolled = False
    employee.face_enrolled_at = None
    update_fields = ['face_embedding', 'is_face_enrolled', 'face_enrolled_at']
    if employee.profile_photo:
        try:
            employee.profile_photo.delete(save=False)
        except Exception:
            pass
        employee.profile_photo = None
        update_fields.append('profile_photo')
    employee.save(update_fields=update_fields)

    messages.success(request, f"Face enrollment removed for {employee.get_full_name() or employee.username}. Worker can now re-enroll.")
    return redirect('employee_detail', pk=pk)

