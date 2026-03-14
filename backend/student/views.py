from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import StudentProfile, Course, Enrollment, Attendance, FeeRecord, AcademicRecord

def get_student_profile(request):
    """Helper method to get the current student profile from session."""
    student_email = request.session.get('student_email')
    if student_email:
        return StudentProfile.objects.filter(user__email=student_email).first()
    return StudentProfile.objects.first() # Fallback for demo


def student_dashboard(request):
    try:
        student_profile = get_student_profile(request)
        if not student_profile:
             return render(request, "dashboards/student/overview_new.html", {"error": "No student profile found for this user."})

        enrollments = Enrollment.objects.filter(student=student_profile)
        attendance_records = Attendance.objects.filter(student=student_profile).order_by('-date')
        fee_records = FeeRecord.objects.filter(student=student_profile)
        academic_records = AcademicRecord.objects.filter(student=student_profile)

        total_attendance = attendance_records.count()
        present_count = attendance_records.filter(status='Present').count()
        attendance_percentage = (present_count / total_attendance * 100) if total_attendance > 0 else 0

        total_due = sum(fee.amount_due - fee.amount_paid for fee in fee_records if fee.status != 'Paid')
        total_paid = sum(fee.amount_paid for fee in fee_records)

        context = {
            'profile': student_profile,
            'enrollments': enrollments,
            'attendance_percentage': round(attendance_percentage, 1),
            'attendance_records': attendance_records[:10],  # Show recent 10
            'fee_records': fee_records,
            'records': academic_records,  # For grades tab
            'total_due': total_due,
            'total_paid': total_paid,
        }
        return render(request, "dashboards/student/overview_new.html", context)
    except Exception as e:
        return render(request, "dashboards/student/overview_new.html", {"error": str(e)})

def student_attendance(request):
    profile = get_student_profile(request)
    if not profile:
        return redirect('login')

    from datetime import datetime
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Base query for attendance
    attendance_qs = Attendance.objects.filter(student=profile)
    if start_date:
        attendance_qs = attendance_qs.filter(date__gte=start_date)
    if end_date:
        attendance_qs = attendance_qs.filter(date__lte=end_date)

    # Get all enrolled courses to group them
    enrollments = Enrollment.objects.filter(student=profile).select_related('course')
    
    # Grouping logic: Group by base code (e.g., AL-602 and AL-602[P])
    course_groups = {}
    
    from backend.faculty.models import FacultyCourseAssignment
    
    for en in enrollments:
        course = en.course
        base_code = course.code.replace('[P]', '')
        
        if base_code not in course_groups:
            # Find faculty for the theory part primarily, or whatever is available
            faculty_assignment = FacultyCourseAssignment.objects.filter(course__code__icontains=base_code).first()
            faculty_name = faculty_assignment.faculty.user.name if faculty_assignment else "TBD"
            
            course_groups[base_code] = {
                'name': course.name.replace(' Lab', '').replace(' practical', ''),
                'base_code': base_code,
                'faculty': faculty_name,
                'theory': {'total': 0, 'present': 0, 'absent': 0, 'records': []},
                'practical': {'total': 0, 'present': 0, 'absent': 0, 'records': []},
                'total_all': 0,
                'present_all': 0,
            }
        
        # Determine if theory or practical
        is_practical = '[P]' in course.code
        category = 'practical' if is_practical else 'theory'
        
        # Get attendance for this specific course variation
        course_attendance = attendance_qs.filter(course=course).order_by('-date')
        
        course_groups[base_code][category]['total'] += course_attendance.count()
        course_groups[base_code][category]['present'] += course_attendance.filter(status='Present').count()
        course_groups[base_code][category]['absent'] += course_attendance.filter(status='Absent').count()
        
        # Merge records for detailed view
        for att in course_attendance:
            course_groups[base_code][category]['records'].append(att)
            course_groups[base_code]['total_all'] += 1
            if att.status == 'Present':
                course_groups[base_code]['present_all'] += 1

    # Calculate global indicators
    total_theory = 0
    present_theory = 0
    total_practical = 0
    present_practical = 0
    
    course_data_list = []
    for base_code, data in course_groups.items():
        total_theory += data['theory']['total']
        present_theory += data['theory']['present']
        total_practical += data['practical']['total']
        present_practical += data['practical']['present']
        
        # Calculate individual course percentage
        total = data['total_all']
        present = data['present_all']
        data['percentage'] = (present / total * 100) if total > 0 else 0
        
        # Sort records by date for the detailed view
        all_records = data['theory']['records'] + data['practical']['records']
        data['all_records'] = sorted(all_records, key=lambda x: x.date, reverse=True)
        
        course_data_list.append(data)

    global_theory_pct = (present_theory / total_theory * 100) if total_theory > 0 else 0
    global_practical_pct = (present_practical / total_practical * 100) if total_practical > 0 else 0
    
    total_overall = total_theory + total_practical
    present_overall = present_theory + present_practical
    global_overall_pct = (present_overall / total_overall * 100) if total_overall > 0 else 0

    return render(request, "dashboards/student/attendance.html", {
        'profile': profile,
        'global_theory_pct': round(global_theory_pct, 1),
        'global_practical_pct': round(global_practical_pct, 1),
        'global_overall_pct': round(global_overall_pct, 1),
        'course_data': course_data_list,
        'start_date': start_date_str,
        'end_date': end_date_str
    })

def student_fees(request):
    profile = get_student_profile(request)
    records = FeeRecord.objects.filter(student=profile)
    total_due = sum(fee.amount_due for fee in records if fee.status != 'Paid')
    return render(request, "dashboards/student/fees.html", {'profile': profile, 'records': records, 'total_due': total_due})

def student_courses(request):
    profile = get_student_profile(request)
    records = Enrollment.objects.filter(student=profile)
    return render(request, "dashboards/student/courses.html", {'profile': profile, 'records': records})

def student_academics(request):
    profile = get_student_profile(request)
    records = AcademicRecord.objects.filter(student=profile)
    return render(request, "dashboards/student/academics.html", {'profile': profile, 'records': records})
