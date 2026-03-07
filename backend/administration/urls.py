from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('students/', views.manage_students, name='manage_students'),
    path('faculty/', views.manage_faculty, name='manage_faculty'),
    path('fees/', views.fee_management, name='fee_management'),
]
