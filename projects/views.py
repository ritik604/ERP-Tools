from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Avg, DecimalField, FloatField
from django.db.models.functions import Coalesce
from .models import ProjectSite, Milestone, MilestoneImage
from .forms import ProjectSiteForm, MilestoneForm
from fuel.models import FuelRecord
import csv
from django.http import HttpResponse

@login_required
def project_list(request):
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    
    query = request.GET.get('q')
    status_filter = request.GET.get('status')

    projects = ProjectSite.objects.all()

    if query:
        projects = projects.filter(Q(name__icontains=query) | Q(site_id__icontains=query))
    
    if status_filter:
        projects = projects.filter(status=status_filter)

    # Optimization: Prefetch related data to avoid N+1 queries
    projects = projects.prefetch_related('milestones', 'fuel_records')
    
    projects_list = []
    for project in projects:
        # Calculate Progress
        milestones = project.milestones.all()
        if milestones:
            project.calculated_progress = sum(m.progress for m in milestones) / len(milestones)
        else:
            project.calculated_progress = 0
            
        # Calculate Expense
        fuel_records = project.fuel_records.all()
        project.calculated_expense = sum(fr.total_cost for fr in fuel_records)
        
        projects_list.append(project)

    return render(request, 'projects/project_list.html', {'projects': projects_list})

@login_required
def project_create(request):
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ProjectSiteForm(request.POST)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'Project Site "{project.name}" created!')
            return redirect('projects:project_list')
    else:
        form = ProjectSiteForm()
    
    return render(request, 'projects/project_form.html', {'form': form})

@login_required
def project_detail(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')

    project = get_object_or_404(ProjectSite, pk=pk)
    
    if request.method == 'POST':
        milestone_form = MilestoneForm(request.POST, request.FILES)
        if milestone_form.is_valid():
            milestone = milestone_form.save(commit=False)
            milestone.project = project
            milestone.save()
            
            # Handle multiple images
            files = request.FILES.getlist('images')
            for f in files:
                MilestoneImage.objects.create(milestone=milestone, image=f)
                
            messages.success(request, "Milestone added successfully!")
            return redirect('projects:project_detail', pk=pk)
        else:
            with open('debug_upload.log', 'a') as f_log:
                f_log.write(f"Form Errors: {milestone_form.errors.as_json()}\n")
    else:
        milestone_form = MilestoneForm()

    milestones = project.milestones.all().order_by('deadline')
    
    # Calculate analytics
    total_milestones = milestones.count()
    completed_milestones = milestones.filter(status='COMPLETED').count()
    
    # Use average progress of all milestones for overall progress
    if total_milestones > 0:
        overall_progress = sum(m.progress for m in milestones) / total_milestones
    else:
        overall_progress = 0
    
    # Calculate actual expense from fuel records
    total_expense = FuelRecord.objects.filter(project=project).aggregate(total=Sum('total_cost'))['total'] or 0.00
    
    # Calculate days spent
    days_spent = (timezone.now().date() - project.start_date).days
    if days_spent < 0: days_spent = 0

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'milestones': milestones,
        'milestone_form': milestone_form,
        'project_form': ProjectSiteForm(instance=project),  # For update modal
        'now': timezone.now(),
        'total_milestones': total_milestones,
        'completed_milestones': completed_milestones,
        'completion_percentage': round(overall_progress, 1),
        'total_expense': total_expense,
        'days_spent': days_spent,
    })

@login_required
def project_update(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    project = get_object_or_404(ProjectSite, pk=pk)
    
    if request.method == 'POST':
        form = ProjectSiteForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project Site "{project.name}" updated!')
            return redirect('projects:project_detail', pk=pk)
    else:
        form = ProjectSiteForm(instance=project)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'project': project,
        'is_update': True
    })

@login_required
def milestone_update(request, pk, milestone_id):
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
    
    project = get_object_or_404(ProjectSite, pk=pk)
    milestone = get_object_or_404(Milestone, pk=milestone_id, project=project)
    
    if request.method == 'POST':
        form = MilestoneForm(request.POST, request.FILES, instance=milestone)
        if form.is_valid():
            milestone = form.save()
            
            # Handle image deletions
            delete_images = request.POST.get('delete_images', '')
            if delete_images:
                image_ids = [int(id) for id in delete_images.split(',') if id.strip()]
                for image_id in image_ids:
                    try:
                        image = MilestoneImage.objects.get(pk=image_id, milestone=milestone)
                        image.image.delete()  # Delete the file
                        image.delete()  # Delete the record
                    except MilestoneImage.DoesNotExist:
                        pass
            
            # Handle multiple new images
            files = request.FILES.getlist('images')
            for f in files:
                MilestoneImage.objects.create(milestone=milestone, image=f)

            messages.success(request, f"Milestone '{milestone.name}' updated successfully!")
            return redirect('projects:project_detail', pk=pk)
    else:
        form = MilestoneForm(instance=milestone)
    
    return render(request, 'projects/milestone_update.html', {
        'project': project,
        'milestone': milestone,
        'form': form
    })


@login_required
def milestone_image_delete(request, pk, milestone_id, image_id):
    """Delete a milestone image."""
    project = get_object_or_404(ProjectSite, pk=pk)
    milestone = get_object_or_404(Milestone, pk=milestone_id, project=project)
    image = get_object_or_404(MilestoneImage, pk=image_id, milestone=milestone)
    
    if request.method == 'POST':
        image.image.delete()  # Delete the actual file
        image.delete()  # Delete the database record
        messages.success(request, "Image deleted successfully!")
    
    return redirect('projects:milestone_update', pk=pk, milestone_id=milestone_id)

@login_required
def project_delete(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
        
    project = get_object_or_404(ProjectSite, pk=pk)
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, f'Project "{project.name}" deleted successfully!')
        return redirect('projects:project_list')
        
    return render(request, 'projects/project_confirm_delete.html', {'project': project})

@login_required
def export_projects_csv(request):
    """View for exporting project site data to CSV."""
    if request.user.role != 'ADMIN':
        messages.error(request, "Access Denied.")
        return redirect('dashboard')
        
    query = request.GET.get('q')
    status_filter = request.GET.get('status')
    
    projects = ProjectSite.objects.all()
    if query:
        projects = projects.filter(Q(name__icontains=query) | Q(site_id__icontains=query))
    if status_filter:
        projects = projects.filter(status=status_filter)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="projects_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Site ID', 'Name', 'Budget', 'Status', 'Start Date'])
    
    for proj in projects:
        writer.writerow([
            proj.site_id,
            proj.name,
            proj.budget,
            proj.get_status_display(),
            proj.start_date.strftime("%Y-%m-%d") if proj.start_date else ""
        ])
        
    return response
