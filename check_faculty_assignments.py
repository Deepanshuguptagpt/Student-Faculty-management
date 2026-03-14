import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.faculty.models import FacultyCourseAssignment
from authentication.models import User

# List all faculty assignments to see why they might not show up
users = User.objects.filter(role='faculty')
print(f"Total faculty users: {users.count()}")

assignments = FacultyCourseAssignment.objects.all()
print(f"Total faculty assignments: {assignments.count()}")

for a in assignments:
    print(f"Faculty: {a.faculty.user.email} | Course: {a.course.name} | Semester: {a.semester}")
