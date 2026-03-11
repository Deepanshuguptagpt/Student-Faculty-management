import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile

def main():
    # Load new students from excel
    df = pd.read_excel('CS2_with_emails.xlsx')
    count = 0
    
    for index, row in df.iterrows():
        name = str(row['Name']).strip()
        email = str(row['Email']).strip()
        enrollment_number = str(row['Roll No']).strip()
        
        if not name or not email or name == 'nan' or email == 'nan':
            continue
            
        # We assume 2023 since enrollment ID may contain something like '23'
        try:
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
        # Keep them in 'Computer science engineering' branch to group with existing ones
        profile, profile_created = StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                'enrollment_number': enrollment_number,
                'batch_year': batch_year,
                'branch': 'Computer science engineering',
                'course_name': 'B.tech',
                'section': 'CSE-2'
            }
        )
        count += 1

    print(f"Finished importing {count} CS2 students into CSE-2 section, under Computer science engineering.")

if __name__ == "__main__":
    main()
