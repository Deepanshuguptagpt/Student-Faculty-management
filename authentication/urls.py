from django.urls import path
from . import views

urlpatterns = [

path('',views.landing),

path('login-options/',views.login_options),

path('login/<str:role>/',views.login_view),
path('dashboard/student/',views.student_dashboard, name='student_dashboard'),
path('dashboard/faculty/',views.faculty_dashboard, name='faculty_dashboard'),
path('dashboard/admin/',views.admin_dashboard, name='admin_dashboard'),

]