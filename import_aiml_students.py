import os
import django
import sys
import pandas as pd

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import StudentProfile, Course, Enrollment, SEMESTER_CHOICES
from authentication.models import User
from django.db import transaction

def import_students(excel_file_path):
    print(f"Reading {excel_file_path}...")
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        print(f"Error reading excel file: {e}")
        return

    # Assuming columns are like 'Enrollment No.', 'Name', 'Email'
    # Try to find the exact column names
    cols = df.columns.tolist()
    print(f"Columns found: {cols}")
    
    # Simple mapping - adjust to actual column names
    enrollment_col = next((c for c in cols if 'enrollment' in str(c).lower()), None)
    name_col = next((c for c in cols if 'name' in str(c).lower()), None)
    email_col = next((c for c in cols if 'email' in str(c).lower()), None)
    
    if not (enrollment_col and name_col and email_col):
        # Specific names per user screenshot if matching fails
        enrollment_col = cols[1] if len(cols) > 1 else 'Enrollment'
        name_col = cols[2] if len(cols) > 2 else 'Name'
        email_col = cols[3] if len(cols) > 3 else 'Email'
        print(f"Using guessed columns: Enroll={enrollment_col}, Name={name_col}, Email={email_col}")

    # Start database transaction
    with transaction.atomic():
        print("Deleting existing test students...")
        # Get users associated with students first to delete them too
        student_user_ids = StudentProfile.objects.values_list('user_id', flat=True)
        User.objects.filter(id__in=student_user_ids).delete()
        print(f"Deleted {len(student_user_ids)} student users and profiles.")

        # Let's see if there is an AIML branch/course representation.
        # From earlier exploration, there's no Branch model, just Course (Subject)
        # So we'll enroll these students in the existing CS101 for the demo, 
        # or create a new course representing an AIML subject and enroll them.
        
        # Look for course the faculty is assigned to (CS101)
        course, created = Course.objects.get_or_create(
            code='CS101', 
            defaults={'name': 'Introduction to Computer Science', 'credits': 3}
        )
        print(f"Using Course for enrollment: {course}")
        
        new_profiles = []
        new_enrollments = []
        
        for index, row in df.iterrows():
            enr = str(row[enrollment_col]).strip()
            name = str(row[name_col]).strip()
            email = str(row[email_col]).strip()
            
            if not enr or not email or str(enr) == 'nan' or str(email) == 'nan':
                continue
                
            # print(f"Processing: {enr} - {name} - {email}")
            
            # Create User
            user, u_created = User.objects.get_or_create(
                email=email,
                defaults={
                    'name': name,
                    'role': 'student',
                }
            )
            # Set a default password instead of random for testing
            if hasattr(user, 'set_password'):
                user.set_password('password123')
            else:
                user.password = 'password123'
            user.save()
            
            # Create StudentProfile
            profile, p_created = StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    'enrollment_number': enr,
                    'batch_year': 2023, 
                    'branch': 'Artificial Intelligence and machine Learning',
                    'course_name': 'Artificial Intelligence and machine Learning'
                }
            )
            
            # Enroll the student in the course the faculty teaches so they show up in "Load Students"
            enrollment, e_created = Enrollment.objects.get_or_create(
                student=profile,
                course=course,
                semester='1st Semester'
            )
            
            new_profiles.append(profile)
            
        print(f"Successfully processed {len(new_profiles)} students and enrolled them in {course.code}.")

if __name__ == '__main__':
    file_path = 'aiml_with_correct_emails.xlsx'
    import_students(file_path)

