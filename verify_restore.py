import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile, Attendance, Enrollment

print(f"Total Users: {User.objects.count()}")
print(f"Faculty Count: {User.objects.filter(role='faculty').count()}")
print(f"Student Count: {User.objects.filter(role='student').count()}")
print(f"Total Attendance Records: {Attendance.objects.count()}")

# Ensure admin exists
admin_email = 'admin@college.edu'
admin_user, created = User.objects.get_or_create(
    email=admin_email,
    defaults={
        'name': 'System Admin',
        'role': 'admin',
        'password': 'password123'
    }
)
if created:
    print(f"Created new admin: {admin_email} / password123")
else:
    print(f"Admin already exists: {admin_email}")
