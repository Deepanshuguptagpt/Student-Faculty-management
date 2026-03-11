import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile

def main():
    # Update existing AIML students
    aiml_students = StudentProfile.objects.filter(branch='Artificial Intelligence and machine Learning')
    updated = aiml_students.update(section='AIML-1')
    print(f"Updated {updated} AIML students to section AIML-1.")

    # Load new students from excel
    df = pd.read_excel('CSE1.xlsx')
    count = 0
    
    for index, row in df.iterrows():
        name = row['Name']
        email = row['Email']
        enrollment_number = row['Enrollment No']
        
        # We assume 2023 since enrollment ID may contain something like '23'
        try:
            # 0818CS231001
            year_str = str(enrollment_number)[8:10]
            if year_str.isdigit():
                batch_year = int("20" + year_str)
            else:
                batch_year = 2023
        except:
            batch_year = 2023

        user, user_created = User.objects.get_or_create(email=email, defaults={
            'name': name,
            'role': 'student',
            'password': 'ADMIN'
        })
        
        # Create or update StudentProfile
        profile, profile_created = StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                'enrollment_number': enrollment_number,
                'batch_year': batch_year,
                'branch': 'Computer science engineering',
                'course_name': 'B.tech',
                'section': 'CSE-1'
            }
        )
        count += 1

    print(f"Finished importing {count} CSE-1 students.")

if __name__ == "__main__":
    main()
