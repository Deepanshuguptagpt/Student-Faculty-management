from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/attendance/', views.student_attendance, name='student_attendance'),
    path('dashboard/fees/', views.student_fees, name='student_fees'),
    path('dashboard/courses/', views.student_courses, name='student_courses'),
    path('dashboard/academics/', views.student_academics, name='student_academics'),
]