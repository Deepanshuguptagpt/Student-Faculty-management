from django.shortcuts import render, redirect

def landing(request):
    return render(request,'authentication/landing.html')


def login_options(request):
    return render(request,'authentication/login_choice.html')


def login_view(request, role):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        if password == "ADMIN":

            if role == "student":
                return redirect("/dashboard/student/")

            elif role == "faculty":
                return redirect("/dashboard/faculty/")

            elif role == "admin":
                return redirect("/dashboard/admin/")

    return render(request,'authentication/login.html',{"role":role})

def student_dashboard(request):
    return render(request,'dashboards/student_dashboard.html')


def faculty_dashboard(request):
    return render(request,'dashboards/faculty_dashboard.html')


def admin_dashboard(request):
    return render(request,'dashboards/admin_dashboard.html')