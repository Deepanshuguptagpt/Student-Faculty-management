from django.shortcuts import render, redirect
from authentication.models import User
from backend.student.models import StudentProfile, FeeRecord
from .models import FacultyProfile

def admin_dashboard(request):
    total_students = StudentProfile.objects.count()
    total_faculty = FacultyProfile.objects.count()
    
    # Calculate fee analytics
    all_fees = FeeRecord.objects.all()
    total_collected = sum(f.amount_paid for f in all_fees)
    total_pending = sum(f.amount_due for f in all_fees if f.status != 'Paid')
    
    context = {
        'total_students': total_students,
        'total_faculty': total_faculty,
        'total_collected': total_collected,
        'total_pending': total_pending,
    }
    return render(request, "dashboards/admin/overview.html", context)


def manage_students(request):
    students = StudentProfile.objects.all().select_related('user')
    return render(request, "dashboards/admin/students.html", {'students': students})


def manage_faculty(request):
    faculty = FacultyProfile.objects.all().select_related('user')
    return render(request, "dashboards/admin/faculty.html", {'faculty': faculty})


def fee_management(request):
    fees = FeeRecord.objects.all().select_related('student__user').order_by('-due_date')
    total_dues = sum(f.amount_due for f in fees if f.status != 'Paid')
    return render(request, "dashboards/admin/fees.html", {'fees': fees, 'total_dues': total_dues})
