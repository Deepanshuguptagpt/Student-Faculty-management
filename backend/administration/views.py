from django.shortcuts import render, redirect
from authentication.models import User
from backend.student.models import StudentProfile, FeeRecord, BRANCH_CHOICES, COURSE_CHOICES, SEMESTER_CHOICES
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
    
    branch_filter = request.GET.get('branch')
    year_filter = request.GET.get('year')
    course_filter = request.GET.get('course')

    if branch_filter:
        students = students.filter(branch=branch_filter)
    if year_filter:
        students = students.filter(batch_year=year_filter)
    if course_filter:
        students = students.filter(course_name=course_filter)

    return render(request, "dashboards/admin/students.html", {
        'students': students, 
        'selected_branch': branch_filter, 
        'selected_year': year_filter, 
        'selected_course': course_filter,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'courses': [c[0] for c in COURSE_CHOICES]
    })


def manage_faculty(request):
    faculty = FacultyProfile.objects.all().select_related('user')
    return render(request, "dashboards/admin/faculty.html", {'faculty': faculty})


def fee_management(request):
    fees = FeeRecord.objects.all().select_related('student__user').order_by('-due_date')
    
    branch_filter = request.GET.get('branch')
    semester_filter = request.GET.get('semester')
    course_filter = request.GET.get('course')

    if branch_filter:
        fees = fees.filter(student__branch=branch_filter)
    if semester_filter:
        fees = fees.filter(semester=semester_filter)
    if course_filter:
        fees = fees.filter(student__course_name=course_filter)

    total_dues = sum(f.amount_due for f in fees if f.status != 'Paid')
    return render(request, "dashboards/admin/fees.html", {
        'fees': fees, 
        'total_dues': total_dues,
        'selected_branch': branch_filter,
        'selected_semester': semester_filter,
        'selected_course': course_filter,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'courses': [c[0] for c in COURSE_CHOICES],
        'semesters': [s[0] for s in SEMESTER_CHOICES]
    })
