import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.faculty.models import FacultyCourseAssignment
from backend.student.models import Enrollment, Attendance, Course

# Check assignments for Atish Mishra
try:
    fac = FacultyCourseAssignment.objects.filter(faculty__user__name='Atish Mishra')
    print("Atish Mishra teaches:")
    for assignment in fac:
        print(f" - {assignment.course.name} ({assignment.course.code})")

    fac = FacultyCourseAssignment.objects.filter(faculty__user__name='Shivani Katare')
    print("\nShivani Katare teaches:")
    for assignment in fac:
        print(f" - {assignment.course.name} ({assignment.course.code})")

    # Check some enrollments
    aiml_enrollments = Enrollment.objects.filter(student__branch__iexact='Artificial Intelligence and machine Learning').count()
    print(f"\nTotal AIML student enrollments created: {aiml_enrollments}")

    b1_student = Enrollment.objects.filter(student__enrollment_number='0818CL231010').first()
    if b1_student:
        print(f"\nSample B1 student '{b1_student.student.enrollment_number}' has {b1_student.student.enrollments.count()} enrollments.")
    else:
        print("\nCould not find test B1 student.")    

except Exception as e:
    print(e)
