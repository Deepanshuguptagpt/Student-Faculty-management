from django.shortcuts import render, redirect
from django.urls import reverse
from .models import User
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth import authenticate, login

def landing(request):
    return render(request,'authentication/landing.html')


def login_options(request):
    return render(request,'authentication/login_choice.html')


def login_view(request, role):

    error = None

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        # ADMIN LOGIN (Django superuser)
        if role == "admin":
            try:
                admin_user = DjangoUser.objects.get(email=email)

                user = authenticate(username=admin_user.username, password=password)

                if user is not None:
                    login(request, user)
                    return redirect("/admin-panel/dashboard/")
                else:
                    error = "Invalid admin credentials"

            except DjangoUser.DoesNotExist:
                error = "Admin not found"


        # STUDENT / FACULTY LOGIN
        else:
            try:
                user = User.objects.get(email=email)

                if user.password != password:
                    error = "Invalid password"

                elif user.role != role:
                    error = "Access denied for this role"

                else:

                    if role == "student":
                        request.session['student_email'] = email
                        return redirect("/student/dashboard/")

                    elif role == "faculty":
                        request.session['faculty_email'] = email
                        return redirect("/faculty/dashboard/")

            except User.DoesNotExist:
                error = "User not registered"

    return render(request,'authentication/login.html',{"role":role,"error":error})

def student_dashboard(request):
    return render(request,'dashboards/student_dashboard.html')


def faculty_dashboard(request):
    return render(request,'dashboards/faculty_dashboard.html')


def admin_dashboard(request):
    return render(request,'dashboards/admin_dashboard.html')