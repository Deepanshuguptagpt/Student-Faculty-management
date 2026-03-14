import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import StudentProfile, Attendance, Enrollment
from backend.faculty.models import FacultyCourseAssignment

def verify_logic():
    student = StudentProfile.objects.filter(branch__iexact='Artificial Intelligence and machine Learning').first()
    if not student:
        print("No student found.")
        return

    # Simulate logic from view
    enrollments = Enrollment.objects.filter(student=student).select_related('course')
    course_groups = {}
    
    for en in enrollments:
        course = en.course
        base_code = course.code.replace('[P]', '')
        if base_code not in course_groups:
            course_groups[base_code] = {
                'theory': {'total': 0, 'present': 0},
                'practical': {'total': 0, 'present': 0},
            }
        
        is_p = '[P]' in course.code
        cat = 'practical' if is_p else 'theory'
        
        att = Attendance.objects.filter(student=student, course=course)
        course_groups[base_code][cat]['total'] = att.count()
        course_groups[base_code][cat]['present'] = att.filter(status='Present').count()

    total_theory = sum(g['theory']['total'] for g in course_groups.values())
    present_theory = sum(g['theory']['present'] for g in course_groups.values())
    total_practical = sum(g['practical']['total'] for g in course_groups.values())
    present_practical = sum(g['practical']['present'] for g in course_groups.values())
    
    print(f"Theory Summary: {present_theory}/{total_theory} ({(present_theory/total_theory*100 if total_theory > 0 else 0):.1f}%)")
    print(f"Practical Summary: {present_practical}/{total_practical} ({(present_practical/total_practical*100 if total_practical > 0 else 0):.1f}%)")
    
    # Check a dual-mode course group
    for code, data in course_groups.items():
        if data['theory']['total'] > 0 and data['practical']['total'] > 0:
            print(f"Course {code} correctly has both Theory and Practical entries.")
            break

if __name__ == '__main__':
    verify_logic()
