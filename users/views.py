from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import CustomUser
from projects.models import ProjectSite
from attendance.models import Attendance
from django.db.models import Sum, Q
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserUpdateForm
import csv

@login_required
def dashboard_view(request):
    user = request.user
    context = {}
    
    if user.role == 'ADMIN':
        context['title'] = "Admin Dashboard"
        context['total_projects'] = ProjectSite.objects.filter(status='ACTIVE').count()
        context['total_employees'] = CustomUser.objects.filter(role__in=['SUPERVISOR', 'WORKER']).exclude(is_superuser=True).count()
        context['total_budget'] = ProjectSite.objects.aggregate(Sum('budget'))['budget__sum'] or 0
    elif user.role == 'SUPERVISOR':
        context['title'] = "Supervisor Dashboard"
        # Assuming supervisor is assigned to a site or manages workers based on some logic
        # For now simply count workers
        context['assigned_workers'] = CustomUser.objects.filter(role='WORKER').count()
    elif user.role == 'WORKER':
        context['title'] = "Worker Dashboard"
        last_attendance = Attendance.objects.filter(worker=user).order_by('-check_in_time').first()
        context['last_checkin'] = last_attendance.check_in_time if last_attendance else None
        # Ensure last_login is fresh from the user object
        context['last_login'] = user.last_login
    
    return render(request, 'users/dashboard.html', context)


@login_required
def register(request):
    if request.user.role == 'WORKER':
        messages.error(request, "You are not authorized to create users.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request_user=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Supervisor strict permission check
            if request.user.role == 'SUPERVISOR':
                if user.role != 'WORKER':
                    messages.error(request, "Supervisors can only create Workers.")
                    return redirect('register')
            
            user.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm(request_user=request.user)
    return render(request, 'users/register.html', {'form': form})

@login_required
def employee_list(request):
    if request.user.role not in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    if request.user.role == 'ADMIN':
        employees = CustomUser.objects.filter(role__in=['SUPERVISOR', 'WORKER']).exclude(is_superuser=True).select_related('assigned_site')
    else:
        # Supervisor sees only workers
        employees = CustomUser.objects.filter(role='WORKER').select_related('assigned_site')
    
    # Filtering
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    site_filter = request.GET.get('site', '')
    
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
    
    # Get all sites for filter dropdown
    sites = ProjectSite.objects.all()

    # Pagination
    employees = employees.order_by('employee_id')
    paginator = Paginator(employees, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_count': employees.count(),
        'sites': sites,
        'search_query': search_query,
        'role_filter': role_filter,
        'site_filter': site_filter,
        'is_admin': request.user.role == 'ADMIN',
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'users/employee_table_partial.html', context)
    
    return render(request, 'users/employee_list.html', context)


@login_required
def employee_detail(request, pk):
    if request.user.role not in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    employee = get_object_or_404(CustomUser, pk=pk)
    
    # Supervisors can only view workers
    if request.user.role == 'SUPERVISOR' and employee.role != 'WORKER':
        messages.error(request, "Access Denied.")
        return redirect('employee_list')
    
    return render(request, 'users/employee_detail.html', {'employee': employee, 'is_admin': request.user.role == 'ADMIN'})

@login_required
def employee_update(request, pk):
    # Only ADMIN can update
    if request.user.role != 'ADMIN':
        messages.error(request, "Only Admins can update employee details.")
        return redirect('employee_list')
    
    employee = get_object_or_404(CustomUser, pk=pk)

    if not employee.is_active:
        messages.error(request, "Updates are not allowed on deactivated profiles. Please activate the profile first.")
        return redirect('employee_detail', pk=pk)

    if request.method == 'POST':
        form = CustomUserUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f'Employee {employee.username} updated successfully!')
            return redirect('employee_detail', pk=pk)
    else:
        form = CustomUserUpdateForm(instance=employee)
    
    return render(request, 'users/employee_edit.html', {'form': form, 'employee': employee})


@login_required
def toggle_employee_status(request, pk):
    if request.user.role != 'ADMIN':
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
    if request.user.role not in ['ADMIN', 'SUPERVISOR']:
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    if request.user.role == 'ADMIN':
        employees = CustomUser.objects.filter(role__in=['SUPERVISOR', 'WORKER']).exclude(is_superuser=True).select_related('assigned_site')
    else:
        employees = CustomUser.objects.filter(role='WORKER').select_related('assigned_site')
    
    # Apply filters
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    site_filter = request.GET.get('site', '')
    
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
    
    # Generate CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employees_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Name', 'Role', 'Assigned Site', 'Salary', 'Mobile', 'Government ID'])
    
    for emp in employees:
        writer.writerow([
            emp.employee_id,
            emp.get_full_name() or emp.username,
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
    if request.user.role != 'ADMIN':
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
