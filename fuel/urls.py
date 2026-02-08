from django.urls import path
from . import views

app_name = 'fuel'

urlpatterns = [
    path('', views.fuel_list, name='fuel_list'),
    path('new/', views.fuel_create, name='fuel_create'),
    path('<int:pk>/', views.fuel_detail, name='fuel_detail'),
    path('<int:pk>/edit/', views.fuel_update, name='fuel_update'),
    path('<int:pk>/delete/', views.fuel_delete, name='fuel_delete'),
    path('export/', views.export_fuel_csv, name='fuel_export_csv'),
]
