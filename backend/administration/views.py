from django.shortcuts import render, redirect
from authentication.models import User
from backend.student.models import StudentProfile, FeeRecord, BRANCH_CHOICES, COURSE_CHOICES, SEMESTER_CHOICES
from backend.faculty.models import FacultyProfile

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
    from datetime import date
    students = StudentProfile.objects.all().select_related('user')
    
    branch_filter = request.GET.get('branch')
    year_filter = request.GET.get('year')
    course_filter = request.GET.get('course')

    if branch_filter:
        students = students.filter(branch=branch_filter)
    if year_filter:
        # Filter by current year (1st, 2nd, 3rd, 4th)
        current_year = date.today().year
        current_month = date.today().month
        year_num = int(year_filter.split()[0][0])  # Extract number from "1st year", "2nd year", etc.
        
        # Calculate batch years that correspond to this year level
        if current_month >= 7:
            # After July, new academic year has started
            target_batch = current_year - (year_num - 1)
        else:
            # Before July, still in previous academic year
            target_batch = current_year - year_num
        
        students = students.filter(batch_year=target_batch)
    if course_filter:
        students = students.filter(course_name=course_filter)

    year_choices = ['1st year', '2nd year', '3rd year', '4th year']

    return render(request, "dashboards/admin/students.html", {
        'students': students, 
        'selected_branch': branch_filter, 
        'selected_year': year_filter, 
        'selected_course': course_filter,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'courses': [c[0] for c in COURSE_CHOICES],
        'years': year_choices
    })


def manage_faculty(request):
    faculty = FacultyProfile.objects.all().select_related('user', 'department').order_by('department__name')
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

def add_student(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name')
        if not User.objects.filter(email=email).exists():
            user = User.objects.create(email=email, name=name, role='student', password='ADMIN')
            StudentProfile.objects.create(
                user=user,
                enrollment_number=request.POST.get('enrollment_number'),
                branch=request.POST.get('branch'),
                course_name=request.POST.get('course_name'),
                batch_year=request.POST.get('batch_year'),
                contact_number=request.POST.get('contact_number'),
                section=request.POST.get('section')
            )
        return redirect('manage_students')
    return render(request, 'dashboards/admin/student_form.html', {
        'action': 'Add',
        'branches': [b[0] for b in BRANCH_CHOICES],
        'courses': [c[0] for c in COURSE_CHOICES]
    })

def edit_student(request, student_id):
    student = StudentProfile.objects.get(id=student_id)
    if request.method == 'POST':
        student.user.name = request.POST.get('name')
        student.user.email = request.POST.get('email')
        student.user.save()
        
        student.enrollment_number = request.POST.get('enrollment_number')
        student.branch = request.POST.get('branch')
        student.course_name = request.POST.get('course_name')
        student.batch_year = request.POST.get('batch_year')
        student.contact_number = request.POST.get('contact_number')
        student.section = request.POST.get('section')
        student.save()
        return redirect('manage_students')
        
    return render(request, 'dashboards/admin/student_form.html', {
        'action': 'Edit',
        'student': student,
        'user_obj': student.user,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'courses': [c[0] for c in COURSE_CHOICES]
    })

def delete_student(request, student_id):
    student = StudentProfile.objects.get(id=student_id)
    student.user.delete() # Automatically cascades to StudentProfile
    return redirect('manage_students')

def add_faculty(request):
    from backend.faculty.models import Department
    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name')
        if not User.objects.filter(email=email).exists():
            user = User.objects.create(email=email, name=name, role='faculty', password='ADMIN')
            dept = Department.objects.get(id=request.POST.get('department_id'))
            FacultyProfile.objects.create(
                user=user,
                department=dept,
                designation=request.POST.get('designation'),
                contact_number=request.POST.get('contact_number')
            )
        return redirect('manage_faculty')
    return render(request, 'dashboards/admin/faculty_form.html', {
        'action': 'Add',
        'departments': Department.objects.all()
    })

def edit_faculty(request, faculty_id):
    from backend.faculty.models import Department
    faculty = FacultyProfile.objects.get(id=faculty_id)
    if request.method == 'POST':
        faculty.user.name = request.POST.get('name')
        faculty.user.email = request.POST.get('email')
        faculty.user.save()
        
        faculty.department = Department.objects.get(id=request.POST.get('department_id'))
        faculty.designation = request.POST.get('designation')
        faculty.contact_number = request.POST.get('contact_number')
        faculty.save()
        return redirect('manage_faculty')
        
    return render(request, 'dashboards/admin/faculty_form.html', {
        'action': 'Edit',
        'faculty': faculty,
        'user_obj': faculty.user,
        'departments': Department.objects.all()
    })

def delete_faculty(request, faculty_id):
    faculty = FacultyProfile.objects.get(id=faculty_id)
    faculty.user.delete() # Automatically cascades
    return redirect('manage_faculty')
