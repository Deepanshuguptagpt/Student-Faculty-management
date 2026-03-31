from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('dashboard/profile/', views.faculty_profile, name='faculty_profile'),
    path('dashboard/courses/', views.faculty_courses, name='faculty_courses'),
    path('dashboard/attendance/', views.faculty_attendance, name='faculty_attendance'),
    path('dashboard/attendance/ai/', views.faculty_attendance_ai, name='faculty_attendance_ai'),
    path('dashboard/analytics/', views.faculty_analytics, name='faculty_analytics'),
    path('dashboard/assignments/', views.faculty_assignments, name='faculty_assignments'),
    path('dashboard/assignments/<int:assignment_id>/', views.faculty_assignment_detail, name='faculty_assignment_detail'),
]
