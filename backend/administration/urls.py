from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard_root'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('students/', views.manage_students, name='manage_students'),
    path('faculty/', views.manage_faculty, name='manage_faculty'),
    path('fees/', views.fee_management, name='fee_management'),
    path('fees/initialize/', views.initialize_default_fees, name='initialize_default_fees'),
    
    path('students/add/', views.add_student, name='add_student'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),

    path('faculty/add/', views.add_faculty, name='add_faculty'),
    path('faculty/edit/<int:faculty_id>/', views.edit_faculty, name='edit_faculty'),
    path('faculty/delete/<int:faculty_id>/', views.delete_faculty, name='delete_faculty'),
]
