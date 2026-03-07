from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import FacultyProfile, FacultyCourseAssignment, Department
from backend.student.models import Attendance, Course, Enrollment, StudentProfile

def get_faculty_profile(request):
    faculty_email = request.session.get('faculty_email')
    if faculty_email:
        return FacultyProfile.objects.filter(user__email=faculty_email).first()
    return FacultyProfile.objects.first() # Fallback for demo


def faculty_dashboard(request):
    try:
        profile = get_faculty_profile(request)
        if not profile:
            return render(request, "dashboards/faculty/overview.html", {"error": "No faculty profile found for this user."})
        
        assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
        total_courses = assignments.count()
        total_credits = sum(a.course.credits for a in assignments)
        
        # Approximate students taught
        course_ids = assignments.values_list('course_id', flat=True)
        total_students = Enrollment.objects.filter(course_id__in=course_ids).values('student').distinct().count()
        
        context = {
            'profile': profile,
            'total_courses': total_courses,
            'total_credits': total_credits,
            'total_students': total_students,
            'assignments': assignments[:5]
        }
        return render(request, "dashboards/faculty/overview.html", context)
    except Exception as e:
        return render(request, "dashboards/faculty/overview.html", {"error": str(e)})

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
    assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        date = request.POST.get("date")
        student_ids = request.POST.getlist("student_ids")
        statuses = request.POST.getlist("statuses")
        
        # For simplicity, if taking attendance
        if course_id and date and student_ids:
            course = Course.objects.get(id=course_id)
            for student_id, status in zip(student_ids, statuses):
                student = StudentProfile.objects.get(id=student_id)
                Attendance.objects.update_or_create(
                    student=student, course=course, date=date,
                    defaults={"status": status}
                )
            
            return redirect('/faculty/dashboard/attendance/?success=1')
    
    # If selected a course to view/take attendance
    selected_course_id = request.GET.get('course_id')
    students = []
    if selected_course_id:
        enrollments = Enrollment.objects.filter(course_id=selected_course_id)
        students = [en.student for en in enrollments]
        
    context = {
        'profile': profile,
        'assignments': assignments,
        'students': students,
        'selected_course_id': int(selected_course_id) if selected_course_id else None
    }
    return render(request, "dashboards/faculty/attendance.html", context)

def faculty_analytics(request):
    profile = get_faculty_profile(request)
    assignments = FacultyCourseAssignment.objects.filter(faculty=profile)
    course_ids = assignments.values_list('course_id', flat=True)
    
    analytics_data = []
    for assignment in assignments:
        course = assignment.course
        total_classes = Attendance.objects.filter(course=course).values('date').distinct().count()
        enrollments = Enrollment.objects.filter(course=course)
        
        student_stats = []
        for en in enrollments:
            student = en.student
            present = Attendance.objects.filter(student=student, course=course, status='Present').count()
            attendance_percent = (present / total_classes * 100) if total_classes > 0 else 0
            student_stats.append({
                'student': student,
                'attendance_percent': attendance_percent
            })
            
        analytics_data.append({
            'course': course,
            'total_classes': total_classes,
            'student_stats': student_stats
        })
        
    context = {
        'profile': profile,
        'analytics_data': analytics_data
    }
    return render(request, "dashboards/faculty/analytics.html", context)
