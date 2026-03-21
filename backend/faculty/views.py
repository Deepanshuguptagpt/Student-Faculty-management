from django.shortcuts import render, redirect
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
            due_date = request.POST.get('due_date')
            attachment = request.FILES.get('attachment')
            
            # Validation: Due date cannot be in the past
            if due_date:
                selected_date = datetime.datetime.strptime(due_date, '%Y-%m-%d').date()
                if selected_date < datetime.date.today():
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
                    due_date=due_date if due_date else None,
                    attachment=attachment
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
        due_date = request.POST.get('due_date')
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
                due_date=due_date if due_date else None,
                attachment=attachment
            )
        return redirect('faculty_assignments')
        
    from .models import Assignment
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
    
    return render(request, "dashboards/faculty/assignments.html", {
        'profile': profile,
        'courses': courses,
        'branches': [b[0] for b in BRANCH_CHOICES],
        'years': year_choices,
        'assignments': assignments,
        'selected_branch': branch_filter,
        'selected_year': year_filter,
        'selected_course': course_filter
    })

def faculty_assignment_detail(request, assignment_id):
    profile = get_faculty_profile(request)
    from .models import Assignment, AssignmentSubmission
    assignment = Assignment.objects.get(id=assignment_id, faculty=profile)
    submissions = AssignmentSubmission.objects.filter(assignment=assignment).select_related('student__user')
    
    if request.method == 'POST' and request.POST.get('action') == 'grade':
        submission_id = request.POST.get('submission_id')
        grade = request.POST.get('grade')
        feedback = request.POST.get('feedback')
        sub = AssignmentSubmission.objects.get(id=submission_id, assignment=assignment)
        sub.grade = grade
        sub.feedback = feedback
        sub.save()
        return redirect('faculty_assignment_detail', assignment_id=assignment_id)
        
    return render(request, "dashboards/faculty/assignment_detail.html", {
        'profile': profile,
        'assignment': assignment,
        'submissions': submissions
    })
