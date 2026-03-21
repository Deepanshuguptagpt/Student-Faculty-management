from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import StudentProfile, Course, Enrollment, Attendance, FeeRecord, AcademicRecord
from .utils import calculate_detailed_attendance

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

        # Calculate pending assignments for notification count
        from backend.faculty.models import Assignment, AssignmentSubmission
        for enrollment in enrollments:
            total_assignments = Assignment.objects.filter(course=enrollment.course, branch=student_profile.branch).count()
            submitted_count = AssignmentSubmission.objects.filter(
                assignment__course=enrollment.course, 
                assignment__branch=student_profile.branch,
                student=student_profile
            ).count()
            enrollment.pending_assignments = total_assignments - submitted_count

        attendance_data = calculate_detailed_attendance(student_profile)

        total_due = sum(fee.amount_due - fee.amount_paid for fee in fee_records if fee.status != 'Paid')
        total_paid = sum(fee.amount_paid for fee in fee_records)

        context = {
            'profile': student_profile,
            'enrollments': enrollments,
            'attendance_percentage': attendance_data['global_overall_pct'],
            'attendance_records': attendance_records[:10],  # Show recent 10
            'fee_records': fee_records,
            'records': academic_records,  # For grades tab
            'total_due': total_due,
            'total_paid': total_paid,
        }
        return render(request, "dashboards/student/overview_new.html", context)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return render(request, "dashboards/student/overview_new.html", {"error": str(e)})

def student_attendance(request):
    profile = get_student_profile(request)
    if not profile:
        return redirect('login')

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    attendance_data = calculate_detailed_attendance(profile, start_date_str, end_date_str)

    return render(request, "dashboards/student/attendance.html", {
        'profile': profile,
        'global_theory_pct': attendance_data['global_theory_pct'],
        'global_practical_pct': attendance_data['global_practical_pct'],
        'global_overall_pct': attendance_data['global_overall_pct'],
        'course_data': attendance_data['course_data'],
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
    
    # Calculate pending assignments for notification count
    from backend.faculty.models import Assignment, AssignmentSubmission
    for enrollment in records:
        total = Assignment.objects.filter(course=enrollment.course, branch=profile.branch).count()
        submitted = AssignmentSubmission.objects.filter(
            assignment__course=enrollment.course, 
            assignment__branch=profile.branch,
            student=profile
        ).count()
        enrollment.pending_assignments = total - submitted

    return render(request, "dashboards/student/courses.html", {'profile': profile, 'records': records})

def student_course_assignments(request, course_id):
    profile = get_student_profile(request)
    course = Course.objects.get(id=course_id)
    from backend.faculty.models import Assignment, AssignmentSubmission
    assignments = Assignment.objects.filter(course=course, branch=profile.branch).order_by('-created_at')
    
    # Enrich assignments with student's current submission status
    for a in assignments:
        a.my_submission = AssignmentSubmission.objects.filter(assignment=a, student=profile).first()
        
    return render(request, "dashboards/student/course_assignments.html", {
        'profile': profile,
        'course': course,
        'assignments': assignments
    })

def student_submit_assignment(request, assignment_id):
    profile = get_student_profile(request)
    from backend.faculty.models import Assignment, AssignmentSubmission
    assignment = Assignment.objects.get(id=assignment_id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        attachment = request.FILES.get('attachment')
        
        AssignmentSubmission.objects.update_or_create(
            assignment=assignment,
            student=profile,
            defaults={
                'content': content,
                'attachment': attachment
            }
        )
        return redirect('student_course_assignments', course_id=assignment.course.id)
        
    submission = AssignmentSubmission.objects.filter(assignment=assignment, student=profile).first()
    return render(request, "dashboards/student/submit_assignment.html", {
        'profile': profile,
        'assignment': assignment,
        'submission': submission
    })

def student_academics(request):
    profile = get_student_profile(request)
    records = AcademicRecord.objects.filter(student=profile)
    return render(request, "dashboards/student/academics.html", {'profile': profile, 'records': records})
