import os
import django
import pandas as pd

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile, Course, Enrollment

def main():
    excel_file = 'Ds-Student-List.xlsx'
    print(f"Reading {excel_file}...")
    
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        print(f"Error reading {excel_file}: {e}")
        return

    # Ensure a basic DS course exists
    ds_course, _ = Course.objects.get_or_create(
        code='DS101',
        defaults={'name': 'Introduction to Data Science', 'credits': 4}
    )
    python_course = Course.objects.filter(code='PYTH').first()

    count = 0
    for index, row in df.iterrows():
        name = str(row['StudentName']).strip()
        email = str(row['Email']).strip()
        enrollment_number = str(row['RollNo']).strip()
        
        if not name or not email or name == 'nan' or email == 'nan':
            continue
            
        try:
            if 'CD' in enrollment_number:
                idx = enrollment_number.find('CD')
                year_str = enrollment_number[idx+2:idx+4]
            else:
                year_str = enrollment_number[8:10]
            batch_year = int("20" + year_str) if year_str.isdigit() else 2023
        except:
            batch_year = 2023

        # Force clear anyone else with this enrollment number
        StudentProfile.objects.filter(enrollment_number=enrollment_number).exclude(user__email=email).delete()

        # Get or create user
        user, created = User.objects.get_or_create(email=email, defaults={
            'name': name,
            'role': 'student',
            'password': 'ADMIN'
        })
        
        if not created:
            user.name = name
            user.save()

        # Create or update profile
        profile, p_created = StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                'enrollment_number': enrollment_number,
                'batch_year': batch_year,
                'branch': 'Data science',
                'course_name': 'B.tech',
                'section': 'DS-1'
            }
        )

        # Enroll in courses
        Enrollment.objects.get_or_create(
            student=profile,
            course=ds_course,
            defaults={'semester': '1st Semester'}
        )
        if python_course:
            Enrollment.objects.get_or_create(
                student=profile,
                course=python_course,
                defaults={'semester': '1st Semester'}
            )

        count += 1
        if count % 10 == 0:
            print(f"Processed {count} students...")

    print(f"\nImport successful. Total students: {count}")
    print(f"Enrolled students in {ds_course.code}" + (f" and {python_course.code}" if python_course else ""))

if __name__ == "__main__":
    main()
