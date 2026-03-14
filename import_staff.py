import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.faculty.models import FacultyProfile, Department, FacultyCourseAssignment
from backend.student.models import Course

print("Deleting all existing faculty data...")
User.objects.filter(role='faculty').delete()

with open('faculty_data.json', 'r', encoding='utf-8') as f:
    faculties = json.load(f)

def get_code(name):
    # Some names might have special characters or be single words
    words = name.replace('-', ' ').strip().split()
    if len(words) == 1:
        return name.strip()[:4].upper()
    
    code = "".join([w[0].upper() for w in words if w.isalpha()])
    if not code:
        return name.strip()[:4].upper()
    return code

print("Importing newly added faculty payload...")
for row in faculties:
    name = row.get("Faculty's Name", "").strip()
    email = row.get("Email", "").strip()
    dept_name = row.get("Department ", "").strip()
    designation = row.get("Designation", "").strip()
    assigned_courses_raw = row.get("Assigned Courses", "").strip()
    
    if not email:
        continue

    # 1. Setup Department
    dept_code = get_code(dept_name)
    dept, _ = Department.objects.get_or_create(
        name=dept_name,
        defaults={'code': dept_code}
    )

    # 2. Setup user with default test password
    user = User.objects.create(
        email=email,
        name=name,
        role='faculty',
        password='password123'
    )
    
    # 3. Setup Faculty Profile
    profile = FacultyProfile.objects.create(
        user=user,
        department=dept,
        designation=designation
    )

    # 4. Bind parsed courses
    if assigned_courses_raw:
        c_names = [c.strip() for c in assigned_courses_raw.split(',')]
        for cn in c_names:
            if not cn: 
                continue
            
            c_code = get_code(cn)
            course, _ = Course.objects.get_or_create(
                code=c_code,
                defaults={'name': cn, 'credits': 3}
            )
            
            FacultyCourseAssignment.objects.get_or_create(
                faculty=profile,
                course=course,
                defaults={'semester': '1st Semester'}
            )

print(f"Successfully imported {len(faculties)} faculty records.")
