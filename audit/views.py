from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q

from .models import AuditLog
from users.models import CustomUser


@login_required
def audit_list(request):
    """List all audit logs with filtering options."""
    # Only admins can view audit trail
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    # Get filter parameters
    query = request.GET.get('q', '')
    module_filter = request.GET.get('module', '')
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Check for export request
    if request.GET.get('export') == 'true':
        return export_audit_csv(request)
    
    # Base queryset
    logs = AuditLog.objects.all().select_related('user')
    
    # Apply filters
    if query:
        logs = logs.filter(
            Q(record_repr__icontains=query) |
            Q(record_id__icontains=query)
        )
    
    if module_filter:
        logs = logs.filter(module=module_filter)
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    # Order by most recent
    logs = logs.order_by('-timestamp')
    
    # Get distinct values for filters
    modules = AuditLog.objects.values_list('module', flat=True).distinct()
    users = CustomUser.objects.filter(
        id__in=AuditLog.objects.values_list('user_id', flat=True).distinct()
    ).order_by('username')
    
    # Pagination
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'modules': sorted(modules),
        'users': users,
        'actions': AuditLog.ACTION_CHOICES,
        'filter_q': query,
        'filter_module': module_filter,
        'filter_action': action_filter,
        'filter_user': user_filter,
        'filter_date_from': date_from,
        'filter_date_to': date_to,
        'total_count': logs.count(),
    }
    
    return render(request, 'audit/audit_list.html', context)


@login_required
def audit_detail(request, pk):
    """View detailed audit log entry."""
    # Only admins can view audit trail
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    log = get_object_or_404(AuditLog, pk=pk)
    
    return render(request, 'audit/audit_detail.html', {'log': log})


@login_required
def export_audit_csv(request):
    """Export filtered audit logs to CSV."""
    if request.user.role != 'ADMIN':
        return HttpResponse("Access Denied", status=403)
    
    import csv
    
    # Apply same filters as list view
    module_filter = request.GET.get('module', '')
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logs = AuditLog.objects.all().select_related('user')
    
    if module_filter:
        logs = logs.filter(module=module_filter)
    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(user_id=user_filter)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    logs = logs.order_by('-timestamp')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Action', 'Module', 'Model', 'Record ID', 'Record', 'Changes', 'IP Address'])
    
    for log in logs:
        writer.writerow([
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.user.username if log.user else 'System',
            log.get_action_display(),
            log.module,
            log.model_name,
            log.record_id,
            log.record_repr,
            str(log.changes),
            log.ip_address or '-'
        ])
    
    return response
