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
        total_classes = Attendance.objects.filter(course=course).values('date', 'lecture_number').distinct().count()
        print(f"Course: {course.name} ({course.code})")
        print(f"  Total classes (distinct date/lecture): {total_classes}")
        
        enrollments = Enrollment.objects.filter(course=course)
        print(f"  Enrollment count: {enrollments.count()}")
        
        for en in enrollments[:3]:
            student = en.student
            present = Attendance.objects.filter(student=student, course=course, status='Present').count()
            absent = Attendance.objects.filter(student=student, course=course, status='Absent').count()
            total_student_records = present + absent
            print(f"    Student: {student.user.name}")
            print(f"      Present: {present}, Absent: {absent}, Total records: {total_student_records}")
            if total_classes > 0:
                print(f"      Current calculation: {present/total_classes*100:.1f}%")
else:
    print("Faculty not found")
