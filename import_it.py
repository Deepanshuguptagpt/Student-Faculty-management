import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile

def main():
    # Load new students from excel
    try:
        df = pd.read_excel('IT_list_with_emails.xlsx')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    count = 0
    
    for index, row in df.iterrows():
        name = str(row['Name']).strip()
        email = str(row['Email']).strip()
        enrollment_number = str(row['Enrollment No']).strip()
        
        if not name or not email or name == 'nan' or email == 'nan':
            continue
            
        if not enrollment_number or enrollment_number == 'nan':
            print(f"Skipping student {name} due to missing enrollment number")
            continue

        # Extract batch year from enrollment number (e.g. 0818CS231001 -> 2023)
        try:
            year_str = str(enrollment_number)[8:10]
            if year_str.isdigit():
                batch_year = int("20" + year_str)
            else:
                batch_year = 2023
        except:
            batch_year = 2023

        # Create or fetch the user model
        user, user_created = User.objects.get_or_create(email=email, defaults={
            'name': name,
            'role': 'student',
            'password': 'ADMIN'
        })
        
        # Check if enrollment number is already used by a DIFFERENT user
        existing_profile = StudentProfile.objects.filter(enrollment_number=enrollment_number).first()
        if existing_profile and existing_profile.user != user:
            print(f"Warning: Enrollment {enrollment_number} already belongs to {existing_profile.user.email}. Skipping {email}.")
            continue

        # Ensure password is set if user is created (or updated if needed)
        # Using Information Technology branch.
        profile, profile_created = StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                'enrollment_number': enrollment_number,
                'batch_year': batch_year,
                'branch': 'Information technology',
                'course_name': 'B.tech',
                'section': 'IT-1' # Default section
            }
        )
        count += 1

    print(f"Successfully imported {count} Information Technology students.")

if __name__ == "__main__":
    main()
