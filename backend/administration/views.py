from django.shortcuts import render, redirect
import json
from authentication.models import User
from backend.student.models import StudentProfile, FeeRecord, BRANCH_CHOICES, COURSE_CHOICES, SEMESTER_CHOICES, FeeMonitoringLog
from backend.faculty.models import FacultyProfile
from django.core.management import call_command
from django.contrib import messages

def admin_dashboard(request):
    total_students = StudentProfile.objects.count()
    total_faculty = FacultyProfile.objects.count()
    
    # Calculate global fee analytics for top stats cards
    all_fees = FeeRecord.objects.all()
    total_collected = sum(f.amount_paid for f in all_fees)
    global_total_pending = sum(f.remaining_amount for f in all_fees)
    
    # Get all students with filters
    students = StudentProfile.objects.all().select_related('user')
    
    # Apply filters
    branch_filter = request.GET.get('branch')
    year_filter = request.GET.get('year')
    course_filter = request.GET.get('course')
    section_filter = request.GET.get('section')
    search_query = request.GET.get('q')
    active_tab = request.GET.get('tab', 'students')
    
    if branch_filter:
        students = students.filter(branch=branch_filter)
    if year_filter:
        from datetime import date
        current_year = date.today().year
        current_month = date.today().month
        year_num = int(year_filter.split()[0][0])
        if current_month >= 7:
            target_batch = current_year - (year_num - 1)
        else:
            target_batch = current_year - year_num
        students = students.filter(batch_year=target_batch)
    if course_filter:
        students = students.filter(course_name=course_filter)
    if section_filter:
        students = students.filter(section=section_filter)
    if search_query:
        from django.db.models import Q
        students = students.filter(
            Q(user__name__icontains=search_query) |
            Q(enrollment_number__icontains=search_query)
        )
    
    # Get faculty and fees for tabs
    faculty = FacultyProfile.objects.all().select_related('user', 'department').order_by('department__name')
    
    # Fee logic for Dashboard tab
    fees_query = FeeRecord.objects.filter(student__in=students).select_related('student__user').order_by('student__enrollment_number', 'semester')
    
    # Calculate dues based on current filtered selection (respecting Search/Branch/Year)
    filtered_total_dues = sum(f.remaining_amount for f in fees_query)

    # Hide already paid historical records for the table view only
    fees = fees_query.exclude(status='Paid')
    
    if active_tab != 'fees':
        fees = fees[:50]
    
    year_choices = ['1st year', '2nd year', '3rd year', '4th year']
    sections = StudentProfile.objects.exclude(section__isnull=True).exclude(section='').values_list('section', flat=True).distinct().order_by('section')
    
    context = {
        'total_students': total_students,
        'total_faculty': total_faculty,
        'total_collected': total_collected,
        'total_pending': global_total_pending,  # Overall institute health
        'total_dues': filtered_total_dues,      # Responsive to filters/search
        'students': students,
        'faculty': faculty,
        'fees': fees,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'years': year_choices,
        'courses': [c[0] for c in COURSE_CHOICES],
        'sections': list(sections),
        'selected_branch': branch_filter,
        'selected_year': year_filter,
        'selected_course': course_filter,
        'selected_section': section_filter,
        'search_query': search_query,
        'active_tab': active_tab,
        'branch_data_json': json.dumps({
            'labels': [b[0] for b in BRANCH_CHOICES],
            'values': [StudentProfile.objects.filter(branch=b[0]).count() for b in BRANCH_CHOICES]
        }),
        'fee_stats_json': json.dumps({
            'labels': ['Paid', 'Pending', 'Overdue'],
            'values': [
                FeeRecord.objects.filter(status='Paid').count(),
                FeeRecord.objects.filter(status='Pending').count(),
                FeeRecord.objects.filter(status='Overdue').count()
            ]
        })
    }
    return render(request, "dashboards/admin/overview_new.html", context)


def manage_students(request):
    from datetime import date
    students = StudentProfile.objects.all().select_related('user')
    
    branch_filter = request.GET.get('branch')
    year_filter = request.GET.get('year')
    course_filter = request.GET.get('course')
    search_query = request.GET.get('q')

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
    
    if search_query:
        from django.db.models import Q
        students = students.filter(
            Q(user__name__icontains=search_query) |
            Q(enrollment_number__icontains=search_query)
        )

    year_choices = ['1st year', '2nd year', '3rd year', '4th year']

    return render(request, "dashboards/admin/students.html", {
        'students': students, 
        'selected_branch': branch_filter, 
        'selected_year': year_filter, 
        'selected_course': course_filter,
        'search_query': search_query,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'courses': [c[0] for c in COURSE_CHOICES],
        'years': year_choices
    })


def manage_faculty(request):
    faculty = FacultyProfile.objects.all().select_related('user', 'department').order_by('department__name')
    return render(request, "dashboards/admin/faculty.html", {'faculty': faculty})


def fee_management(request):
    # Get all students first to ensure everyone is listed
    students = StudentProfile.objects.all().select_related('user')
    
    branch_filter = request.GET.get('branch')
    semester_filter = request.GET.get('semester')
    course_filter = request.GET.get('course')
    search_query = request.GET.get('q')

    if branch_filter:
        students = students.filter(branch=branch_filter)
    if course_filter:
        students = students.filter(course_name=course_filter)
    if search_query:
        from django.db.models import Q
        students = students.filter(
            Q(user__name__icontains=search_query) |
            Q(enrollment_number__icontains=search_query)
        )

    # Now get fees but filter them by the students we've narrowed down
    fees = FeeRecord.objects.filter(student__in=students).select_related('student__user').order_by('student__enrollment_number', 'semester')
    
    if semester_filter:
        fees = fees.filter(semester=semester_filter)
    else:
        # Per USER request: By default, show only the records that are not fully paid
        # This keeps the dashboard clean and focused on current/pending work
        fees = fees.exclude(status='Paid')
    
    total_dues = sum(f.remaining_amount for f in fees)
    

    logs = FeeMonitoringLog.objects.all().order_by('-date_performed')[:5]
    
    return render(request, "dashboards/admin/fees.html", {
        'fees': fees, 
        'total_dues': total_dues,
        'selected_branch': branch_filter,
        'selected_semester': semester_filter,
        'selected_course': course_filter,
        'search_query': search_query,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'courses': [c[0] for c in COURSE_CHOICES],
        'semesters': [s[0] for s in SEMESTER_CHOICES],
        'agent_logs': logs
    })

def run_fee_agent_view(request):
    try:
        call_command('fee_agent', force=True)
        messages.success(request, "Fee Management Agent executed successfully. Reminder emails sent.")
    except Exception as e:
        messages.error(request, f"Error running Fee Management Agent: {str(e)}")
    return redirect('fee_management')

def initialize_default_fees(request):
    from datetime import date
    students = StudentProfile.objects.all()
    created_count = 0
    
    current_year_now = date.today().year
    current_month_now = date.today().month

    for student in students:
        # Calculate current semester integer
        years_diff = current_year_now - student.batch_year
        if current_month_now >= 7:
            s_int = years_diff * 2 + 1
        else:
            s_int = years_diff * 2
        
        s_int = max(1, s_int)
        
        # Determine the two semesters for the current academic year
        if s_int % 2 != 0: # Odd (1, 3, 5, 7)
            sem_a = s_int
            sem_b = s_int + 1
        else: # Even (2, 4, 6, 8)
            sem_a = s_int - 1
            sem_b = s_int
            
        for i in [sem_a, sem_b]:
            if i > 8: continue # Only up to 8th semester
            
            suffix = "th"
            if i == 1: suffix = "st"
            elif i == 2: suffix = "nd"
            elif i == 3: suffix = "rd"
            sem_str = f"{i}{suffix} Semester"
            
            fee, created = FeeRecord.objects.get_or_create(
                student=student,
                semester=sem_str,
                defaults={
                    'amount_due': 60000.00,
                    'amount_paid': 0.00,
                    'due_date': date(current_year_now, 6, 30) if i % 2 == 0 else date(current_year_now, 12, 31),
                    'status': 'Pending'
                }
            )
            if created:
                created_count += 1
                
    return redirect('admin_dashboard') # Redirect to main dashboard

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
