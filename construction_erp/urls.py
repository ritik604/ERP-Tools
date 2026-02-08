from django.contrib import admin
from django.urls import path, include
from users import views as user_views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', user_views.dashboard_view, name='dashboard'),
    path('register/', user_views.register, name='register'),
    path('employees/', user_views.employee_list, name='employee_list'),
    path('employees/view/<int:pk>/', user_views.employee_detail, name='employee_detail'),
    path('employees/edit/<int:pk>/', user_views.employee_update, name='employee_update'),
    path('employees/toggle/<int:pk>/', user_views.toggle_employee_status, name='toggle_employee_status'),
    path('employees/reset-password/<int:pk>/', user_views.reset_password, name='reset_password'),
    path('employees/export/', user_views.export_employees_csv, name='export_employees_csv'),
    path('profile/', user_views.profile, name='profile'),
    path('profile/change-password/', user_views.change_password, name='change_password'),
    
    # App URLs
    path('projects/', include('projects.urls')),
    path('attendance/', include('attendance.urls')),
    path('fuel/', include('fuel.urls')),
    path('vehicles/', include('vehicles.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

