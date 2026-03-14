import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.faculty.models import FacultyProfile, FacultyCourseAssignment
from backend.student.models import Attendance, Enrollment

faculty = FacultyProfile.objects.filter(user__name__icontains='Ratnesh').first()
if faculty:
    print(f"Faculty: {faculty.user.name}")
    assignments = FacultyCourseAssignment.objects.filter(faculty=faculty)
    for a in assignments:
        course = a.course
        print(f"Course: {course.name} ({course.code})")
        
        enrollments = Enrollment.objects.filter(course=course)
        
        for en in enrollments[:3]:
            student = en.student
            # NEW LOGIC
            student_total_classes = Attendance.objects.filter(student=student, course=course).count()
            present = Attendance.objects.filter(student=student, course=course, status='Present').count()
            
            attendance_percent = (present / student_total_classes * 100) if student_total_classes > 0 else 0
            
            print(f"    Student: {student.user.name}")
            print(f"      Present/Total: {present}/{student_total_classes}")
            print(f"      Calculated Percentage: {attendance_percent:.1f}%")
else:
    print("Faculty not found")
