from django.urls import path
from . import views

urlpatterns = [

path('',views.landing),

path('login-options/',views.login_options),

path('login/<str:role>/',views.login_view),

]