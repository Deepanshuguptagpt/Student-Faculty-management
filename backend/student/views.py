from django.shortcuts import render, redirect, get_object_or_404
from functools import wraps
import logging
from .models import StudentProfile, Course, Enrollment, Attendance, FeeRecord, AcademicRecord
from .utils import calculate_detailed_attendance

logger = logging.getLogger(__name__)


def student_login_required(view_func):
    """Decorator that checks for a valid student session."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('student_email'):
            return redirect('/auth/login/student/')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_student_profile(request):
    """Helper method to get the current student profile from session."""
    student_email = request.session.get('student_email')
    if student_email:
        return StudentProfile.objects.filter(user__email=student_email).first()
    return None  # No fallback — caller must handle None


@student_login_required
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
        from backend.faculty.models import Assignment, AssignmentSubmission, SubjectNote
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
            'attendance_records': attendance_records[:10],
            'fee_records': fee_records,
            'records': academic_records,
            'total_due': total_due,
            'total_paid': total_paid,
            'notes_list': SubjectNote.objects.filter(branch=student_profile.branch, year=student_profile.current_year).order_by('-uploaded_at'),
        }
        return render(request, "dashboards/student/overview_new.html", context)
    except Exception as e:
        logger.error(f"Student dashboard error: {e}", exc_info=True)
        return render(request, "dashboards/student/overview_new.html", {"error": str(e)})


@student_login_required
def student_attendance(request):
    profile = get_student_profile(request)
    if not profile:
        return redirect('/auth/login/student/')

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


@student_login_required
def student_fees(request):
    profile = get_student_profile(request)
    records = FeeRecord.objects.filter(student=profile)
    total_due = sum(fee.amount_due for fee in records if fee.status != 'Paid')
    return render(request, "dashboards/student/fees.html", {'profile': profile, 'records': records, 'total_due': total_due})


@student_login_required
def student_courses(request):
    profile = get_student_profile(request)
    records = Enrollment.objects.filter(student=profile)
    
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


@student_login_required
def student_course_assignments(request, course_id):
    profile = get_student_profile(request)
    course = get_object_or_404(Course, id=course_id)
    from backend.faculty.models import Assignment, AssignmentSubmission
    from django.utils import timezone
    assignments = Assignment.objects.filter(course=course, branch=profile.branch).order_by('-created_at')

    for a in assignments:
        a.my_submission = AssignmentSubmission.objects.filter(assignment=a, student=profile).first()

    return render(request, "dashboards/student/course_assignments.html", {
        'profile': profile,
        'course': course,
        'assignments': assignments,
        'now': timezone.now(),
    })


@student_login_required
def student_submit_assignment(request, assignment_id):
    profile = get_student_profile(request)
    from backend.faculty.models import Assignment, AssignmentSubmission
    from django.utils import timezone
    assignment = get_object_or_404(Assignment, id=assignment_id)

    if request.method == 'POST':
        # Guard 1: offline assignments cannot be submitted via portal
        if assignment.submission_mode == 'offline':
            return redirect('student_submit_assignment', assignment_id=assignment_id)

        # Guard 2: block submission after due date
        if assignment.due_datetime and timezone.now() > assignment.due_datetime:
            return redirect('student_submit_assignment', assignment_id=assignment_id)

        content = request.POST.get('content')
        attachment = request.FILES.get('attachment')

        submission = AssignmentSubmission.objects.filter(assignment=assignment, student=profile).first()

        # Guard 3: Document submission is mandatory for online
        if not attachment and not (submission and submission.attachment):
            return render(request, "dashboards/student/submit_assignment.html", {
                'profile': profile,
                'assignment': assignment,
                'submission': submission,
                'is_past_due': False,
                'error': 'A document/PDF attachment is mandatory for your submission.'
            })

        defaults_dict = {'content': content}
        if attachment:
            defaults_dict['attachment'] = attachment

        AssignmentSubmission.objects.update_or_create(
            assignment=assignment,
            student=profile,
            defaults=defaults_dict
        )
        return redirect('student_course_assignments', course_id=assignment.course.id)

    submission = AssignmentSubmission.objects.filter(assignment=assignment, student=profile).first()
    is_past_due = assignment.due_datetime and timezone.now() > assignment.due_datetime
    return render(request, "dashboards/student/submit_assignment.html", {
        'profile': profile,
        'assignment': assignment,
        'submission': submission,
        'is_past_due': is_past_due,
    })


@student_login_required
def student_academics(request):
    profile = get_student_profile(request)
    records = AcademicRecord.objects.filter(student=profile)
    return render(request, "dashboards/student/academics.html", {'profile': profile, 'records': records})
