from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('list/', views.attendance_list, name='attendance_list'),
    path('update/<int:pk>/', views.attendance_update, name='attendance_update'),
    path('export/', views.export_attendance_csv, name='attendance_export_csv'),
    path('check-status/', views.check_automation_status, name='check_automation_status'),
]

