import os
import django
import random

# Setup django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import StudentProfile

PARENT_EMAILS = [
    "kanak.rawataiml2023@indoreinstitute.com",
    "deepanshu.guptaaiml2023@indoreinstitute.com",
    "krishna.kavishwaraiml2023@indoreinstitute.com",
    "diksha.akveanaiml2023@indoreinstitute.com"
]

def assign_parent_emails():
    students = StudentProfile.objects.all()
    count = 0
    for student in students:
        student.parent_email = random.choice(PARENT_EMAILS)
        student.save()
        count += 1
    print(f"Successfully assigned random parent emails to {count} students.")

if __name__ == "__main__":
    assign_parent_emails()
