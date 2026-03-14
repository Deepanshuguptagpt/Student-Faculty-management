import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.faculty.models import FacultyProfile, FacultyCourseAssignment

emails = ['atish.mishra@college.edu', 'smita.marwadi@college.edu', 'ratnesh.chaturvedi@college.edu']

for e in emails:
    u = User.objects.filter(email=e).first()
    if u:
        print(f"Found User {u.name} with email {u.email}. Role: {u.role}")
        fp = FacultyProfile.objects.filter(user=u).first()
        if fp:
            print(f" -> Has FacultyProfile.")
            assignments = FacultyCourseAssignment.objects.filter(faculty=fp)
            print(f" -> Has {assignments.count()} assignments.")
        else:
            print(f" -> NO FacultyProfile for this user!")
    else:
        print(f"User with email {e} NOT FOUND!")
        
print("--- Currently logged in (demo) check ---")
# The view says "fallback for demo" is the first FacultyProfile.
fp_first = FacultyProfile.objects.first()
if fp_first:
    print(f"First FacultyProfile: {fp_first.user.name} ({fp_first.user.email})")
    assignments = FacultyCourseAssignment.objects.filter(faculty=fp_first)
    print(f" -> Has {assignments.count()} assignments.")
