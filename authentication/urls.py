from django.urls import path
from . import views

urlpatterns = [
    path('',views.landing),
    path('login-options/',views.login_options),
    path('login/<str:role>/',views.login_view),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/student/',views.student_dashboard, name='auth_student_redirect'),
    path('dashboard/faculty/',views.faculty_dashboard, name='auth_faculty_redirect'),
    path('dashboard/admin/',views.admin_dashboard, name='auth_admin_redirect'),
]