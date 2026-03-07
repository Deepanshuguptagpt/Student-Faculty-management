from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.faculty_dashboard, name='faculty_dashboard'),
    path('dashboard/profile/', views.faculty_profile, name='faculty_profile'),
    path('dashboard/courses/', views.faculty_courses, name='faculty_courses'),
    path('dashboard/attendance/', views.faculty_attendance, name='faculty_attendance'),
    path('dashboard/analytics/', views.faculty_analytics, name='faculty_analytics'),
]
