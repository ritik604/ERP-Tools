from django.contrib import admin
from .models import ProjectSite, Milestone, MilestoneImage

class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0

class MilestoneImageInline(admin.TabularInline):
    model = MilestoneImage
    extra = 0

@admin.register(ProjectSite)
class ProjectSiteAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'name', 'status', 'budget', 'start_date', 'end_date', 'site_radius')
    list_filter = ('status', 'start_date')
    search_fields = ('site_id', 'name')
    ordering = ('-start_date',)
    inlines = [MilestoneInline]

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'progress', 'deadline')
    list_filter = ('status', 'deadline', 'project')
    search_fields = ('name', 'project__name')
    inlines = [MilestoneImageInline]

@admin.register(MilestoneImage)
class MilestoneImageAdmin(admin.ModelAdmin):
    list_display = ('milestone', 'uploaded_at')
