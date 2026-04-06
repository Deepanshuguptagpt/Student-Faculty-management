from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import json
import datetime
import logging
from functools import wraps
from .models import FacultyProfile, FacultyCourseAssignment, Department
from backend.student.models import Attendance, Course, Enrollment, StudentProfile, AttendanceMonitoringLog, BRANCH_CHOICES
import subprocess

logger = logging.getLogger(__name__)

# ── Year choices constant (used everywhere) ──────────────────────────────────
YEAR_CHOICES = ['1st Year', '2nd Year', '3rd Year', '4th Year']


def faculty_login_required(view_func):
    """Decorator that checks for a valid faculty session."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('faculty_email'):
            return redirect('/auth/login/faculty/')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_faculty_profile(request):
    faculty_email = request.session.get('faculty_email')
    if faculty_email:
        return FacultyProfile.objects.filter(user__email=faculty_email).first()
    return None  # No fallback — caller must handle None


@faculty_login_required
def faculty_dashboard(request):
    try:
        profile = get_faculty_profile(request)
        if not profile:
            return render(request, "dashboards/faculty/overview_new.html", {"error": "No faculty profile found for this user."})
        
        # Handle POST request for creating assignment
        if request.method == 'POST' and request.POST.get('action') == 'create_assignment':
            from .models import Assignment
            title = request.POST.get('title')
            description = request.POST.get('description')
            course_id = request.POST.get('course_id')
            branch = request.POST.get('branch')
            year = request.POST.get('year')
            attachment = request.FILES.get('attachment')
            submission_mode = request.POST.get('submission_mode', 'online')

            due_datetime = request.POST.get('due_date')
            selected_dt = None
            if due_datetime:
                from django.utils import timezone
                try:
                    naive_dt = datetime.datetime.strptime(due_datetime, '%Y-%m-%dT%H:%M')
                except ValueError:
                    naive_dt = datetime.datetime.strptime(due_datetime, '%Y-%m-%d')
                    naive_dt = naive_dt.replace(hour=23, minute=59, second=59)
                
                selected_dt = timezone.make_aware(naive_dt)

                if selected_dt.date() < timezone.localdate():
                    return render(request, "dashboards/faculty/overview_new.html", {
                        "profile": profile,
                        "error": "Due date cannot be in the past.",
                        "active_tab": "assignments"
                    })

            if title and course_id and branch:
                assignment = Assignment.objects.create(
                    faculty=profile,
                    title=title,
                    description=description,
                    course_id=course_id,
                    branch=branch,
                    year=year,
                    due_datetime=selected_dt,
                    attachment=attachment,
                    submission_mode=submission_mode,
                )
                
                # Notify enrolled students
                from django.core.mail import send_mail
                from django.conf import settings
                from backend.student.models import StudentProfile
                
                enrolled_students = StudentProfile.objects.filter(branch=branch, enrollments__course_id=course_id).distinct()
                faculty_name = profile.user.name
                
                for student in enrolled_students:
                    subject = f"New Assignment Uploaded: {title}"
                    message = f"Dear {student.user.name},\n\nA new assignment '{title}' has been uploaded by {faculty_name}.\n\nPlease check your dashboard for more details and the due date.\n\nBest regards,\nAcademiq Portal"
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [student.user.email], fail_silently=True)

            return redirect('/faculty/dashboard/?tab=assignments')

        # Handle POST request for extending deadline
        if request.method == 'POST' and request.POST.get('action') == 'extend_deadline':
            from .models import Assignment, AssignmentSubmission
            from django.utils import timezone
            from django.core.mail import send_mail
            from django.conf import settings
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import SystemMessage, HumanMessage
            from ai_assistant.utils import key_rotator

            assignment_id = request.POST.get('assignment_id')
            new_due_date = request.POST.get('new_due_date')
            assignment = Assignment.objects.filter(id=assignment_id, faculty=profile).first()

            if assignment and new_due_date:
                try:
                    naive_dt = datetime.datetime.strptime(new_due_date, '%Y-%m-%dT%H:%M')
                    new_dt = timezone.make_aware(naive_dt)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid date format for deadline extension: {e}")
                    return redirect('/faculty/dashboard/?tab=assignments&error=Invalid date format')
                
                if new_dt <= timezone.now():
                     return redirect('/faculty/dashboard/?tab=assignments&error=Extended deadline must be in the future.')

                assignment.due_datetime = new_dt
                assignment.save()

                # Notify students who haven't submitted
                enrolled_students = StudentProfile.objects.filter(branch=assignment.branch, enrollments__course=assignment.course).distinct()
                for student in enrolled_students:
                    if not AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists():
                        # Agentic Email Generation
                        api_key = key_rotator.get_current_key()
                        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
                        
                        prompt = f"""Write a short, friendly notice to a student about a deadline extension.
Student: {student.user.name}
Assignment: {assignment.title}
New Deadline: {new_dt.strftime('%B %d, %Y at %I:%M %p')}
Tone: Professional and encouraging. 2-3 sentences. No subject line."""
                        
                        try:
                            resp = llm.invoke([SystemMessage(content="You are the Academiq Assistant."), HumanMessage(content=prompt)])
                            body = resp.content.strip()
                        except Exception as e:
                            logger.warning(f"AI email generation failed, using fallback: {e}")
                            body = f"Dear {student.user.name}, the deadline for '{assignment.title}' has been extended to {new_dt.strftime('%B %d, %Y at %I:%M %p')}. Please ensure your submission is completed on time."

                        send_mail(f"Deadline Extended: {assignment.title}", body, settings.DEFAULT_FROM_EMAIL, [student.user.email], fail_silently=True)

                return redirect('/faculty/dashboard/?tab=assignments&extended=1')

        # Handle POST request for uploading notes
        if request.method == 'POST' and request.POST.get('action') == 'upload_note':
            from .models import SubjectNote
            title = request.POST.get('title')
            description = request.POST.get('description')
            course_id = request.POST.get('course_id')
            branch = request.POST.get('branch')
            year = request.POST.get('year')
            file = request.FILES.get('file')

            if title and course_id and branch and file:
                SubjectNote.objects.create(
                    faculty=profile,
                    title=title,
                    description=description,
                    course_id=course_id,
                    branch=branch,
                    year=year,
                    file=file,
                )
            return redirect('/faculty/dashboard/?tab=notes')

        
        assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
        total_courses = assignments.count()
        total_credits = sum(a.course.credits for a in assignments)
        
        # Approximate students taught
        course_ids = assignments.values_list('course_id', flat=True)
        total_students = Enrollment.objects.filter(course_id__in=course_ids).values('student').distinct().count()
        
        # Get workload data
        workload_data = []
        
        # AI Monitoring Logic
        latest_monitoring = AttendanceMonitoringLog.objects.order_by('-date_performed').first()
        
        if request.method == 'POST' and request.POST.get('action') == 'run_ai_agent':
            subprocess.Popen(['python', 'manage.py', 'attendance_agent', '--force'])
            return redirect('/faculty/dashboard/?tab=ai_monitoring&triggered=1')

        for assignment in assignments:
            student_count = Enrollment.objects.filter(course=assignment.course).count()
            workload_data.append({
                'assignment': assignment,
                'student_count': student_count,
                'credits': assignment.course.credits
            })
        
        # Get analytics data
        analytics_data = []
        for assignment in assignments:
            course = assignment.course
            enrollments = Enrollment.objects.filter(course=course)
            
            student_stats = []
            for en in enrollments:
                student = en.student
                student_total_classes = Attendance.objects.filter(student=student, course=course).count()
                present = Attendance.objects.filter(student=student, course=course, status='Present').count()
                attendance_percent = (present / student_total_classes * 100) if student_total_classes > 0 else 0
                student_stats.append({
                    'student': student,
                    'attendance_percent': attendance_percent
                })
                
            analytics_data.append({
                'course': course,
                'total_classes': Attendance.objects.filter(course=course).values('date', 'lecture_number').distinct().count(),
                'student_stats': student_stats
            })
        
        # Get courses for attendance and assignments
        my_course_ids = assignments.values_list('course_id', flat=True)
        my_courses = Course.objects.filter(id__in=my_course_ids)
        courses = Course.objects.filter(id__in=my_course_ids)
        
        # Get assignment data
        from .models import Assignment, SubjectNote
        
        assignment_list = Assignment.objects.filter(faculty=profile).order_by('-created_at')
        
        # Apply filters if coming from assignments tab
        branch_filter = request.GET.get('branch')
        year_filter = request.GET.get('year')
        course_filter = request.GET.get('course')
        active_tab = request.GET.get('tab', 'profile')
        
        if branch_filter:
            assignment_list = assignment_list.filter(branch=branch_filter)
        if year_filter:
            assignment_list = assignment_list.filter(year=year_filter)
        if course_filter:
            assignment_list = assignment_list.filter(course_id=course_filter)
        
        context = {
            'profile': profile,
            'total_courses': total_courses,
            'total_credits': total_credits,
            'total_students': total_students,
            'assignments': assignments[:5],
            'workload_data': workload_data,
            'analytics_data': analytics_data,
            'my_courses': my_courses,
            'courses': courses,
            'branches': [b[0] for b in BRANCH_CHOICES],
            'years': YEAR_CHOICES,
            'assignment_list': assignment_list,
            'selected_branch': branch_filter,
            'selected_year': year_filter,
            'selected_course': course_filter,
            'active_tab': active_tab,
            'latest_monitoring': latest_monitoring,
            'assignment_stats_json': json.dumps({
                'labels': [a.title[:20] + '...' if len(a.title) > 20 else a.title for a in assignment_list[:5]],
                'submitted': [a.submissions.count() for a in assignment_list[:5]],
                'total': [Enrollment.objects.filter(course=a.course).count() for a in assignment_list[:5]]
            }),
            'attendance_stats_json': json.dumps({
                'labels': [d['course'].code for d in analytics_data],
                'values': [
                    (sum(s['attendance_percent'] for s in d['student_stats']) / len(d['student_stats']))
                    if d['student_stats'] else 0
                    for d in analytics_data
                ]
            }),
            'notes_list': SubjectNote.objects.filter(faculty=profile).order_by('-uploaded_at'),
        }
        return render(request, "dashboards/faculty/overview_new.html", context)
    except Exception as e:
        logger.error(f"Faculty dashboard error: {e}", exc_info=True)
        return render(request, "dashboards/faculty/overview_new.html", {"error": str(e)})


@faculty_login_required
def faculty_profile(request):
    profile = get_faculty_profile(request)
    return render(request, "dashboards/faculty/profile.html", {"profile": profile})


@faculty_login_required
def faculty_courses(request):
    profile = get_faculty_profile(request)
    assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    
    workload_data = []
    for assignment in assignments:
        student_count = Enrollment.objects.filter(course=assignment.course).count()
        workload_data.append({
            'assignment': assignment,
            'student_count': student_count,
            'credits': assignment.course.credits
        })
        
    return render(request, "dashboards/faculty/courses.html", {"profile": profile, "workload_data": workload_data})


@faculty_login_required
def faculty_attendance(request):
    profile = get_faculty_profile(request)
    my_assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    my_course_ids = my_assignments.values_list('course_id', flat=True)
    
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        date = request.POST.get("date")
        lecture_number = request.POST.get("lecture_number")
        student_ids = request.POST.getlist("student_ids")
        statuses = request.POST.getlist("statuses")
        
        # Server-side validation for date
        from datetime import datetime as dt_class, date as date_obj
        if date:
            selected_date = dt_class.strptime(date, '%Y-%m-%d').date()
            today = date_obj.today()
            
            if selected_date > today:
                return render(request, "dashboards/faculty/attendance.html", {
                    'profile': profile,
                    'my_courses': Course.objects.filter(id__in=my_course_ids),
                    'other_courses': Course.objects.exclude(id__in=my_course_ids),
                    'error': 'Cannot mark attendance for future dates. Please select today or a previous date.'
                })
            
            if selected_date.weekday() == 6:
                return render(request, "dashboards/faculty/attendance.html", {
                    'profile': profile,
                    'my_courses': Course.objects.filter(id__in=my_course_ids),
                    'other_courses': Course.objects.exclude(id__in=my_course_ids),
                    'error': 'Cannot mark attendance on Sundays. Please select a weekday.'
                })
        
        if course_id and date and lecture_number and student_ids:
            course = get_object_or_404(Course, id=course_id)
            for student_id, status in zip(student_ids, statuses):
                student = get_object_or_404(StudentProfile, id=student_id)
                Attendance.objects.update_or_create(
                    student=student, course=course, date=date, lecture_number=lecture_number,
                    defaults={"status": status}
                )
            
            return redirect('/faculty/dashboard/')
    
    selected_course_id = request.GET.get('course_id')
    selected_date = request.GET.get('date')
    selected_lecture = request.GET.get('lecture_number')
    
    # Server-side validation for GET request
    error_message = None
    if selected_date:
        from datetime import datetime as dt_class, date as date_obj
        try:
            selected_date_obj = dt_class.strptime(selected_date, '%Y-%m-%d').date()
            today = date_obj.today()
            
            if selected_date_obj > today:
                error_message = 'Cannot view attendance for future dates. Please select today or a previous date.'
                selected_date = None
            
            elif selected_date_obj.weekday() == 6:
                error_message = 'Cannot mark attendance on Sundays. Please select a weekday.'
                selected_date = None
        except ValueError:
            error_message = 'Invalid date format.'
            selected_date = None

    students_data = []
    if selected_course_id and selected_date:
        enrollments = Enrollment.objects.filter(course_id=selected_course_id)
        students = [en.student for en in enrollments]
        
        for student in students:
            status = "Present"
            if selected_date and selected_lecture:
                existing = Attendance.objects.filter(
                    student=student, course_id=selected_course_id, date=selected_date, lecture_number=selected_lecture
                ).first()
                if existing:
                    status = existing.status
            students_data.append({
                'student': student,
                'status': status
            })
        
    context = {
        'profile': profile,
        'my_courses': Course.objects.filter(id__in=my_course_ids),
        'other_courses': Course.objects.exclude(id__in=my_course_ids),
        'students_data': students_data,
        'selected_course_id': int(selected_course_id) if selected_course_id else None,
        'selected_date': selected_date,
        'selected_lecture': int(selected_lecture) if selected_lecture else None,
        'error': error_message
    }
    return render(request, "dashboards/faculty/attendance.html", context)


@faculty_login_required
def faculty_analytics(request):
    profile = get_faculty_profile(request)
    assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    
    analytics_data = []
    for assignment in assignments:
        course = assignment.course
        enrollments = Enrollment.objects.filter(course=course)
        
        student_stats = []
        for en in enrollments:
            student = en.student
            student_total_classes = Attendance.objects.filter(student=student, course=course).count()
            present = Attendance.objects.filter(student=student, course=course, status='Present').count()
            attendance_percent = (present / student_total_classes * 100) if student_total_classes > 0 else 0
            student_stats.append({
                'student': student,
                'attendance_percent': attendance_percent
            })
            
        analytics_data.append({
            'course': course,
            'total_classes': Attendance.objects.filter(course=course).values('date', 'lecture_number').distinct().count(),
            'student_stats': student_stats
        })
        
    context = {
        'profile': profile,
        'analytics_data': analytics_data
    }
    return render(request, "dashboards/faculty/analytics.html", context)


@faculty_login_required
def faculty_assignments(request):
    profile = get_faculty_profile(request)
    my_assigned_courses = FacultyCourseAssignment.objects.filter(faculty=profile).values_list('course_id', flat=True)
    from backend.student.models import BRANCH_CHOICES, Course
    courses = Course.objects.filter(id__in=my_assigned_courses)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        course_id = request.POST.get('course_id')
        branch = request.POST.get('branch')
        year = request.POST.get('year')
        due_datetime_raw = request.POST.get('due_date')
        submission_mode = request.POST.get('submission_mode', 'online')
        selected_dt = None
        if due_datetime_raw:
            from django.utils import timezone
            try:
                naive_dt = datetime.datetime.strptime(due_datetime_raw, '%Y-%m-%dT%H:%M')
            except ValueError:
                naive_dt = datetime.datetime.strptime(due_datetime_raw, '%Y-%m-%d')
                naive_dt = naive_dt.replace(hour=23, minute=59, second=59)
            selected_dt = timezone.make_aware(naive_dt)
        attachment = request.FILES.get('attachment')
        
        if title and course_id and branch:
            from .models import Assignment
            assignment = Assignment.objects.create(
                faculty=profile,
                title=title,
                description=description,
                course_id=course_id,
                branch=branch,
                year=year,
                due_datetime=selected_dt if due_datetime_raw else None,
                attachment=attachment,
                submission_mode=submission_mode,
            )
            
            # Notify enrolled students
            from django.core.mail import send_mail
            from django.conf import settings
            from backend.student.models import StudentProfile
            
            enrolled_students = StudentProfile.objects.filter(branch=branch, enrollments__course_id=course_id).distinct()
            faculty_name = profile.user.name
            
            for student in enrolled_students:
                subject = f"New Assignment Uploaded: {title}"
                message = f"Dear {student.user.name},\n\nA new assignment '{title}' has been uploaded by {faculty_name}.\n\nPlease check your dashboard for more details and the due date.\n\nBest regards,\nAcademiq Portal"
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [student.user.email], fail_silently=True)
                
        return redirect('faculty_assignments')

        
    from .models import Assignment, AssignmentSubmission
    from backend.student.models import Enrollment
    from django.utils import timezone
    assignments = Assignment.objects.filter(faculty=profile).order_by('-created_at')

    # Apply filters
    branch_filter = request.GET.get('branch')
    year_filter = request.GET.get('year')
    course_filter = request.GET.get('course')

    if branch_filter:
        assignments = assignments.filter(branch=branch_filter)
    if year_filter:
        assignments = assignments.filter(year=year_filter)
    if course_filter:
        assignments = assignments.filter(course_id=course_filter)

    now = timezone.now()

    # --- Build real per-assignment analytics ---
    assignments_data = []
    total_submitted_all = 0
    total_enrolled_all = 0
    total_graded_all = 0
    total_active = 0
    total_overdue_count = 0

    for a in assignments:
        submitted = a.submissions.count()
        total_enrolled = Enrollment.objects.filter(course=a.course).count()
        pending = max(0, total_enrolled - submitted)
        submission_pct = round((submitted / total_enrolled * 100), 1) if total_enrolled > 0 else 0
        graded = a.submissions.exclude(grade__isnull=True).exclude(grade__exact='').count()
        ungraded = submitted - graded

        if a.due_datetime:
            if now > a.due_datetime:
                deadline_status = 'overdue'
                total_overdue_count += 1
            else:
                deadline_status = 'active'
                total_active += 1
            on_time = a.submissions.filter(submitted_at__lte=a.due_datetime).count()
            late = submitted - on_time
        else:
            deadline_status = 'no_deadline'
            on_time = submitted
            late = 0

        total_submitted_all += submitted
        total_enrolled_all += total_enrolled
        total_graded_all += graded

        assignments_data.append({
            'assignment': a,
            'submitted': submitted,
            'total_enrolled': total_enrolled,
            'pending': pending,
            'submission_pct': submission_pct,
            'graded': graded,
            'ungraded': ungraded,
            'deadline_status': deadline_status,
            'on_time': on_time,
            'late': late,
        })

    total_assignments = len(assignments_data)
    total_pending_all = max(0, total_enrolled_all - total_submitted_all)
    overall_submission_pct = round((total_submitted_all / total_enrolled_all * 100), 1) if total_enrolled_all > 0 else 0

    # Chart data
    chart_labels = []
    chart_submitted = []
    chart_pending = []
    chart_graded = []
    for d in assignments_data[:7]:
        title = d['assignment'].title
        chart_labels.append(title[:22] + '\u2026' if len(title) > 22 else title)
        chart_submitted.append(d['submitted'])
        chart_pending.append(d['pending'])
        chart_graded.append(d['graded'])

    return render(request, "dashboards/faculty/assignments.html", {
        'profile': profile,
        'courses': courses,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'years': YEAR_CHOICES,
        'assignments_data': assignments_data,
        'assignments': [d['assignment'] for d in assignments_data],
        'selected_branch': branch_filter,
        'selected_year': year_filter,
        'selected_course': course_filter,
        'total_assignments': total_assignments,
        'total_submitted_all': total_submitted_all,
        'total_enrolled_all': total_enrolled_all,
        'total_pending_all': total_pending_all,
        'total_graded_all': total_graded_all,
        'total_active': total_active,
        'total_overdue_count': total_overdue_count,
        'overall_submission_pct': overall_submission_pct,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_submitted_json': json.dumps(chart_submitted),
        'chart_pending_json': json.dumps(chart_pending),
        'chart_graded_json': json.dumps(chart_graded),
    })


@faculty_login_required
def faculty_assignment_detail(request, assignment_id):
    profile = get_faculty_profile(request)
    from .models import Assignment, AssignmentSubmission
    from backend.student.models import Enrollment
    from django.utils import timezone
    from collections import defaultdict

    assignment = get_object_or_404(Assignment, id=assignment_id, faculty=profile)
    submissions = AssignmentSubmission.objects.filter(assignment=assignment).select_related('student__user').order_by('submitted_at')

    if request.method == 'POST' and request.POST.get('action') == 'grade':
        submission_id = request.POST.get('submission_id')
        grade = request.POST.get('grade')
        feedback = request.POST.get('feedback')
        sub = get_object_or_404(AssignmentSubmission, id=submission_id, assignment=assignment)
        sub.grade = grade
        sub.feedback = feedback
        sub.save()
        return redirect('faculty_assignment_detail', assignment_id=assignment_id)

    now = timezone.now()
    total_enrolled = Enrollment.objects.filter(course=assignment.course).count()
    submitted_count = submissions.count()
    pending_count = max(0, total_enrolled - submitted_count)
    submission_pct = round((submitted_count / total_enrolled * 100), 1) if total_enrolled > 0 else 0

    graded_count = submissions.exclude(grade__isnull=True).exclude(grade__exact='').count()
    ungraded_count = submitted_count - graded_count

    if assignment.due_datetime:
        on_time_count = submissions.filter(submitted_at__lte=assignment.due_datetime).count()
        late_count = submitted_count - on_time_count
        is_overdue = now > assignment.due_datetime
    else:
        on_time_count = submitted_count
        late_count = 0
        is_overdue = False

    # Grade distribution
    grade_dist = defaultdict(int)
    for sub in submissions:
        g = (sub.grade or 'Ungraded').strip()
        grade_dist[g] += 1
    grade_dist = dict(grade_dist)

    # Submission timeline
    timeline = defaultdict(int)
    for sub in submissions:
        day_key = sub.submitted_at.strftime('%b %d')
        timeline[day_key] += 1
    timeline_labels = list(timeline.keys())
    timeline_values = list(timeline.values())

    return render(request, "dashboards/faculty/assignment_detail.html", {
        'profile': profile,
        'assignment': assignment,
        'submissions': submissions,
        'submitted_count': submitted_count,
        'total_enrolled': total_enrolled,
        'pending_count': pending_count,
        'submission_pct': submission_pct,
        'graded_count': graded_count,
        'ungraded_count': ungraded_count,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'is_overdue': is_overdue,
        'grade_dist_json': json.dumps(grade_dist),
        'timeline_labels_json': json.dumps(timeline_labels),
        'timeline_values_json': json.dumps(timeline_values),
    })


@faculty_login_required
def faculty_attendance_ai(request):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage
    from ai_assistant.utils import key_rotator
    from backend.student.models import Enrollment
    
    profile = get_faculty_profile(request)
    if not profile or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    try:
        data = json.loads(request.body)
        instruction = data.get('instruction')
        course_id = data.get('course_id')

        if not instruction or not course_id:
            return JsonResponse({'success': False, 'error': 'Missing instruction or course_id'})

        enrollments = Enrollment.objects.filter(course_id=course_id).select_related('student__user')
        student_data = []
        for en in enrollments:
            enrollment = en.student.enrollment_number
            last_two = enrollment[-2:] if len(enrollment) >= 2 else enrollment
            last_three = enrollment[-3:] if len(enrollment) >= 3 else enrollment
            student_data.append({
                "id": str(en.student.id),
                "name": en.student.user.name,
                "enrollment_number": enrollment,
                "last_two": last_two,
                "last_three": last_three
            })
            
        student_list_str = "\n".join([
            f"ID: {s['id']}, Name: {s['name']}, Enrollment: {s['enrollment_number']} (Ends with: {s['last_two']} or {s['last_three']})" 
            for s in student_data
        ])

        prompt = f"""You are an AI assistant helping a faculty member mark attendance.
The faculty provided the following natural language instruction: "{instruction}"

Here is the list of enrolled students:
{student_list_str}

Based on the instruction, determine the attendance status ('Present' or 'Absent') ONLY for students explicitly or implicitly mentioned.
Strict Rules for determining status:
1. ONLY return the IDs of students whose attendance needs to be updated based on the instruction.
2. If the instruction says "mark X absent" and doesn't mention the rest, ONLY return student X with status 'Absent'. Do NOT return statuses for anyone else.
3. If the instruction says "mark Y present" and doesn't mention the rest, ONLY return student Y with status 'Present'.
4. If the instruction says "mark X absent, rest all present", then return student X as 'Absent' AND explicitly return all other students as 'Present'.
5. CRITICAL: If the instruction contains numbers (e.g., "mark 23 and 45 absent"), DO NOT treat them as sequence or list numbers. You MUST match those numbers precisely to the "Ends with:" values provided next to each student's Enrollment number.
6. Do your best to fuzzy-match misspelled names from the instruction to the list of enrolled students.

Respond ONLY with a valid JSON format exactly like:
{{
  "results": {{
    "student_id_1": "Present",
    "student_id_2": "Absent"
  }}
}}
Do not include markdown formatting like ```json or any other text.
"""
        max_attempts = len(key_rotator.keys) if hasattr(key_rotator, 'keys') and key_rotator.keys else 1
        output_text = ""
        
        for attempt in range(max_attempts):
            try:
                api_key = key_rotator.get_current_key()
                llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
                resp = llm.invoke([SystemMessage(content="You are a helpful attendance assistant."), HumanMessage(content=prompt)])
                output_text = resp.content.strip()
                break
            except Exception as e:
                error_msg = str(e)
                if ("429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "Quota" in error_msg) and attempt < max_attempts - 1:
                    key_rotator.rotate()
                    continue
                else:
                    raise e
        
        if output_text.startswith("```json"):
            output_text = output_text[7:]
        if output_text.startswith("```"):
            output_text = output_text[3:]
        if output_text.endswith("```"):
            output_text = output_text[:-3]
            
        result_json = json.loads(output_text.strip())
        return JsonResponse({'success': True, 'results': result_json.get('results', {})})

    except Exception as e:
        logger.error(f"Faculty AI attendance error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})
