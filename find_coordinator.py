import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.faculty.models import FacultyProfile, FacultyCourseAssignment
from backend.student.models import StudentProfile

print("Searching for coordinators...")

# Check the attendance agent logic's coordinator
# (Hardcoded in backend/student/management/commands/attendance_agent.py)
coordinator_name = "Mrs. Sukrati Agrawal"
print(f"Coordinator mentioned in Attendance Agent: {coordinator_name}")

# Check faculty profiles in AIML department
aiml_faculty = FacultyProfile.objects.filter(department__name__icontains='Artificial Intelligence')
print("\nFaculty in AIML Department:")
for f in aiml_faculty:
    print(f"- {f.user.name} ({f.designation})")

# Check if anyone is explicitly marked as a coordinator in a way I missed
# Search for 'coordinator' in any data
print("\nChecking for students in AIML Section 1 (AIML-1):")
students = StudentProfile.objects.filter(branch__icontains='Artificial Intelligence', section='AIML-1')
print(f"Found {students.count()} students in AIML-1.")

if students.exists():
    # If there's a specific teacher associated with these students more than others
    pass
