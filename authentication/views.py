from django.shortcuts import render

def landing(request):
    return render(request,'authentication/landing.html')


def login_options(request):
    return render(request,'authentication/login_choice.html')


def login_view(request,role):

    context = {
        "role":role.capitalize()
    }

    return render(request,'authentication/login.html',context)