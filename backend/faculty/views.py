from django.shortcuts import render, redirect
import json
import datetime
from django.contrib.auth.decorators import login_required
from .models import FacultyProfile, FacultyCourseAssignment, Department
from backend.student.models import Attendance, Course, Enrollment, StudentProfile, AttendanceMonitoringLog, BRANCH_CHOICES
import subprocess


def get_faculty_profile(request):
    faculty_email = request.session.get('faculty_email')
    if faculty_email:
        return FacultyProfile.objects.filter(user__email=faculty_email).first()
    return FacultyProfile.objects.first() # Fallback for demo


def faculty_dashboard(request):
    try:
        profile = get_faculty_profile(request)
        if not profile:
            return render(request, "dashboards/faculty/overview_new.html", {"error": "No faculty profile found for this user."})
        
        # Handle POST request for creating assignment
        if request.method == 'POST' and request.POST.get('action') == 'create_assignment':
            from .models import Assignment
            import datetime
            title = request.POST.get('title')
            description = request.POST.get('description')
            course_id = request.POST.get('course_id')
            branch = request.POST.get('branch')
            year = request.POST.get('year')
            attachment = request.FILES.get('attachment')
            submission_mode = request.POST.get('submission_mode', 'online')

            due_datetime = request.POST.get('due_date') # Keep POST name as 'due_date' for form compatibility
            selected_dt = None # Initialize selected_dt
            if due_datetime:
                from django.utils import timezone
                # Handle both date only and datetime strings if possible, 
                # but usually it's %Y-%m-%d from HTML date input.
                # We'll default to end of day if only date is provided.
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
                Assignment.objects.create(
                    faculty=profile,
                    title=title,
                    description=description,
                    course_id=course_id,
                    branch=branch,
                    year=year,
                    due_datetime=selected_dt if due_datetime else None,
                    attachment=attachment,
                    submission_mode=submission_mode,
                )
            return redirect('/faculty/dashboard/?tab=assignments')

        
        assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
        total_courses = assignments.count()
        total_credits = sum(a.course.credits for a in assignments)
        
        # Approximate students taught
        course_ids = assignments.values_list('course_id', flat=True)
        total_students = Enrollment.objects.filter(course_id__in=course_ids).values('student').distinct().count()
        
        # Get workload data
        workload_data = []
        # (Assuming workload_data logic exists below or I should add it if it's not and it's needed for the template)
        
        # AI Monitoring Logic
        latest_monitoring = AttendanceMonitoringLog.objects.order_by('-date_performed').first()
        
        if request.method == 'POST' and request.POST.get('action') == 'run_ai_agent':
            subprocess.Popen(['python', 'manage.py', 'attendance_agent', '--force'])
            return redirect('/faculty/dashboard/?tab=ai_monitoring&triggered=1')

        # Get existing context data (I'll need to see more lines to ensure I don't break existing logic)
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
                # Count records specifically for this student and course
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
        from .models import Assignment
        from backend.student.models import BRANCH_CHOICES
        
        assignment_list = Assignment.objects.filter(faculty=profile).order_by('-created_at')
        
        # Apply filters if coming from assignments tab
        branch_filter = request.GET.get('branch')
        year_filter = request.GET.get('year')
        course_filter = request.GET.get('course')
        active_tab = request.GET.get('tab', 'profile')  # Get active tab from URL
        
        if branch_filter:
            assignment_list = assignment_list.filter(branch=branch_filter)
        if year_filter:
            assignment_list = assignment_list.filter(year=year_filter)
        if course_filter:
            assignment_list = assignment_list.filter(course_id=course_filter)
        
        year_choices = ['1st year', '2nd year', '3rd year', '4th year']
        
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
            'years': year_choices,
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
            })
        }
        return render(request, "dashboards/faculty/overview_new.html", context)
    except Exception as e:
        return render(request, "dashboards/faculty/overview_new.html", {"error": str(e)})

def faculty_profile(request):
    profile = get_faculty_profile(request)
    return render(request, "dashboards/faculty/profile.html", {"profile": profile})

def faculty_courses(request):
    profile = get_faculty_profile(request)
    assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    
    # Calculate workload per course
    workload_data = []
    for assignment in assignments:
        student_count = Enrollment.objects.filter(course=assignment.course).count()
        workload_data.append({
            'assignment': assignment,
            'student_count': student_count,
            'credits': assignment.course.credits
        })
        
    return render(request, "dashboards/faculty/courses.html", {"profile": profile, "workload_data": workload_data})

def faculty_attendance(request):
    profile = get_faculty_profile(request)
    my_assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    my_course_ids = my_assignments.values_list('course_id', flat=True)
    all_courses = Course.objects.all()
    
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        date = request.POST.get("date")
        lecture_number = request.POST.get("lecture_number")
        student_ids = request.POST.getlist("student_ids")
        statuses = request.POST.getlist("statuses")
        
        # Server-side validation for date
        from datetime import datetime, date as date_obj
        if date:
            selected_date = datetime.strptime(date, '%Y-%m-%d').date()
            today = date_obj.today()
            
            # Check if future date
            if selected_date > today:
                return render(request, "dashboards/faculty/attendance.html", {
                    'profile': profile,
                    'my_courses': Course.objects.filter(id__in=my_course_ids),
                    'other_courses': Course.objects.exclude(id__in=my_course_ids),
                    'error': 'Cannot mark attendance for future dates. Please select today or a previous date.'
                })
            
            # Check if Sunday
            if selected_date.weekday() == 6:  # 6 = Sunday
                return render(request, "dashboards/faculty/attendance.html", {
                    'profile': profile,
                    'my_courses': Course.objects.filter(id__in=my_course_ids),
                    'other_courses': Course.objects.exclude(id__in=my_course_ids),
                    'error': 'Cannot mark attendance on Sundays. Please select a weekday.'
                })
        
        # For simplicity, if taking attendance
        if course_id and date and lecture_number and student_ids:
            course = Course.objects.get(id=course_id)
            for student_id, status in zip(student_ids, statuses):
                student = StudentProfile.objects.get(id=student_id)
                Attendance.objects.update_or_create(
                    student=student, course=course, date=date, lecture_number=lecture_number,
                    defaults={"status": status}
                )
            
            return redirect(f'/faculty/dashboard/attendance/?success=1&course_id={course_id}&date={date}&lecture_number={lecture_number}')
    
    # If selected a course to view/take attendance
    selected_course_id = request.GET.get('course_id')
    selected_date = request.GET.get('date')
    selected_lecture = request.GET.get('lecture_number')
    
    # Server-side validation for GET request
    error_message = None
    if selected_date:
        from datetime import datetime, date as date_obj
        try:
            selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            today = date_obj.today()
            
            # Check if future date
            if selected_date_obj > today:
                error_message = 'Cannot view attendance for future dates. Please select today or a previous date.'
                selected_date = None
            
            # Check if Sunday
            elif selected_date_obj.weekday() == 6:  # 6 = Sunday
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

def faculty_analytics(request):
    profile = get_faculty_profile(request)
    assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    course_ids = assignments.values_list('course_id', flat=True)
    
    analytics_data = []
    for assignment in assignments:
        course = assignment.course
        enrollments = Enrollment.objects.filter(course=course)
        
        student_stats = []
        for en in enrollments:
            student = en.student
            # Count records specifically for this student and course
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
            try:
                selected_dt = datetime.datetime.strptime(due_datetime_raw, '%Y-%m-%dT%H:%M')
            except ValueError:
                selected_dt = datetime.datetime.strptime(due_datetime_raw, '%Y-%m-%d')
                selected_dt = selected_dt.replace(hour=23, minute=59, second=59)
        attachment = request.FILES.get('attachment')
        
        if title and course_id and branch:
            from .models import Assignment
            Assignment.objects.create(
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

    year_choices = ['1st year', '2nd year', '3rd year', '4th year']
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

    # Chart: submitted vs pending vs graded for top 7 assignments
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
        'years': year_choices,
        'assignments_data': assignments_data,
        'assignments': [d['assignment'] for d in assignments_data],
        'selected_branch': branch_filter,
        'selected_year': year_filter,
        'selected_course': course_filter,
        # Summary stat cards
        'total_assignments': total_assignments,
        'total_submitted_all': total_submitted_all,
        'total_enrolled_all': total_enrolled_all,
        'total_pending_all': total_pending_all,
        'total_graded_all': total_graded_all,
        'total_active': total_active,
        'total_overdue_count': total_overdue_count,
        'overall_submission_pct': overall_submission_pct,
        # Chart JSON
        'chart_labels_json': json.dumps(chart_labels),
        'chart_submitted_json': json.dumps(chart_submitted),
        'chart_pending_json': json.dumps(chart_pending),
        'chart_graded_json': json.dumps(chart_graded),
    })

def faculty_assignment_detail(request, assignment_id):
    profile = get_faculty_profile(request)
    from .models import Assignment, AssignmentSubmission
    from backend.student.models import Enrollment
    from django.utils import timezone
    from collections import defaultdict

    assignment = Assignment.objects.get(id=assignment_id, faculty=profile)
    submissions = AssignmentSubmission.objects.filter(assignment=assignment).select_related('student__user').order_by('submitted_at')

    if request.method == 'POST' and request.POST.get('action') == 'grade':
        submission_id = request.POST.get('submission_id')
        grade = request.POST.get('grade')
        feedback = request.POST.get('feedback')
        sub = AssignmentSubmission.objects.get(id=submission_id, assignment=assignment)
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

    # On-time vs late
    if assignment.due_datetime:
        on_time_count = submissions.filter(submitted_at__lte=assignment.due_datetime).count()
        late_count = submitted_count - on_time_count
        is_overdue = now > assignment.due_datetime
    else:
        on_time_count = submitted_count
        late_count = 0
        is_overdue = False

    # Grade distribution (letter/numeric grouped)
    grade_dist = defaultdict(int)
    for sub in submissions:
        g = (sub.grade or 'Ungraded').strip()
        grade_dist[g] += 1
    grade_dist = dict(grade_dist)

    # Submission timeline: count per day
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
        # Analytics
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
