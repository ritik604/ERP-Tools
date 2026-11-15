from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('new/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/update/', views.project_update, name='project_update'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('<int:pk>/milestone/new/', views.milestone_create, name='milestone_create'),
    path('<int:pk>/milestone/<int:milestone_id>/update/', views.milestone_update, name='milestone_update'),
    path('<int:pk>/milestone/<int:milestone_id>/delete/', views.milestone_delete, name='milestone_delete'),
    path('export/', views.export_projects_csv, name='project_export_csv'),
]

