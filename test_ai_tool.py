import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.faculty.models import FacultyProfile, FacultyCourseAssignment
from backend.student.models import Attendance, StudentProfile

# Re-defining the tool logic in a testable format to verify the query logic
def test_query_logic(faculty_id, date_str, lecture_number, status):
    print(f"--- Testing attendance query logic for Faculty ID {faculty_id} ---")
    faculty = FacultyProfile.objects.get(id=faculty_id)
    assigned_course_ids = list(
        FacultyCourseAssignment.objects.filter(faculty=faculty)
        .values_list('course_id', flat=True)
    )
    
    from dateutil import parser
    dt = parser.parse(date_str).date()
    
    status_cap = status.strip().capitalize()
    
    query = Attendance.objects.filter(
        date=dt,
        lecture_number=int(lecture_number),
        status=status_cap,
        course_id__in=assigned_course_ids
    ).select_related('student__user', 'course')
    
    if not query.exists():
        print(f"No students marked as '{status_cap}' on {dt} for lecture {lecture_number}.")
        return

    results_by_course = {}
    for att in query:
        c_name = f"{att.course.code} - {att.course.name}"
        if c_name not in results_by_course:
            results_by_course[c_name] = []
        results_by_course[c_name].append(f"  - {att.student.user.name} ({att.student.enrollment_number})")

    output = [f"Students marked as '{status_cap}' on {dt} (Lecture {lecture_number}):"]
    for course, students in results_by_course.items():
        output.append(f"\nCourse: {course}")
        output.extend(students)
    
    print("\n".join(output))

if __name__ == "__main__":
    # Test for Dr. Ratnesh (ID 1)
    # March 25 was one of our backfilled dates.
    test_query_logic(1, "2026-03-25", "3", "Absent")
    print("\n" + "="*40 + "\n")
    test_query_logic(1, "2026-03-25", "3", "Present")
