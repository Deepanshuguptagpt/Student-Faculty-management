import os
import django
import pandas as pd
from django.db import transaction

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile, Course, Enrollment

def get_column(df, patterns):
    for pattern in patterns:
        for col in df.columns:
            if pattern.lower() in str(col).lower():
                return col
    return None

def derive_name(email_prefix):
    # Remove branch/year suffixes like 'cse2023', 'aiml2023', 'it2023', 'ds2023'
    import re
    clean_prefix = re.sub(r'(cse|it|ds|aiml)?\d{4}$', '', email_prefix, flags=re.IGNORECASE)
    # Replace dots with spaces and capitalize
    name_parts = clean_prefix.split('.')
    return ' '.join([p.capitalize() for p in name_parts if p]).strip()

def import_from_file(file_path, branch, section, enrollment_patterns, name_patterns, email_patterns):
    print(f"\nProcessing {file_path}...")
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Skipping.")
        return 0

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

    enr_col = get_column(df, enrollment_patterns)
    name_col = get_column(df, name_patterns)
    email_col = get_column(df, email_patterns)

    if not all([enr_col, name_col, email_col]):
        print(f"Could not find all columns in {file_path}. Found: Enr={enr_col}, Name={name_col}, Email={email_col}")
        return 0

    count = 0
    for _, row in df.iterrows():
        enr = str(row[enr_col]).strip()
        name = str(row[name_col]).strip()
        email = str(row[email_col]).strip()

        if not enr or not email or enr == 'nan' or email == 'nan':
            continue

        # Handle missing or generic names
        if not name or name.lower() in ['nan', 'none', 'name']:
            email_prefix = email.split('@')[0]
            name = derive_name(email_prefix)
            print(f"Derived name '{name}' from email '{email}'")

        # All students are Batch 2023 as per user request
        batch_year = 2023

        with transaction.atomic():
            # Force clear any profile with this enrollment number if it belongs to someone else
            StudentProfile.objects.filter(enrollment_number=enr).exclude(user__email=email).delete()

            # Create/Update User
            user, _ = User.objects.update_or_create(
                email=email, 
                defaults={
                    'name': name,
                    'role': 'student',
                    'password': 'ADMIN'
                }
            )
            
            # Create/Update StudentProfile
            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    'enrollment_number': enr,
                    'batch_year': batch_year,
                    'branch': branch,
                    'course_name': 'B.tech',
                    'section': section
                }
            )
        count += 1
    
    print(f"Imported {count} students from {file_path} into {branch} ({section}).")
    return count

def main():
    total = 0
    
    # Configuration for each branch/file
    configs = [
        {
            'file': 'CSE1.xlsx',
            'branch': 'Computer science engineering',
            'section': 'CSE-1',
            'enr': ['enrollment', 'roll'],
            'name': ['name'],
            'email': ['email']
        },
        {
            'file': 'CS2_with_emails.xlsx',
            'branch': 'Computer science engineering',
            'section': 'CSE-2',
            'enr': ['roll', 'enrollment'],
            'name': ['name'],
            'email': ['email']
        },
        {
            'file': 'CS3_with_emails.xlsx',
            'branch': 'Computer science engineering',
            'section': 'CSE-3',
            'enr': ['enrollment', 'roll'],
            'name': ['name'],
            'email': ['email']
        },
        {
            'file': 'IT_list_with_emails.xlsx',
            'branch': 'Information technology',
            'section': 'IT-1',
            'enr': ['enrollment', 'roll'],
            'name': ['name'],
            'email': ['email']
        },
        {
            'file': 'Ds-Student-List.xlsx',
            'branch': 'Data science',
            'section': 'DS-1',
            'enr': ['roll', 'enrollment'],
            'name': ['studentname', 'name'],
            'email': ['email']
        },
        {
            'file': 'aiml_with_correct_emails.xlsx',
            'branch': 'Artificial Intelligence and machine Learning',
            'section': 'AIML-1',
            'enr': ['enrollment', 'roll'],
            'name': ['name'],
            'email': ['email']
        }
    ]

    for config in configs:
        total += import_from_file(
            config['file'], 
            config['branch'], 
            config['section'],
            config['enr'],
            config['name'],
            config['email']
        )

    print(f"\nTotal students imported/updated: {total}")
    print(f"Current total students in DB: {StudentProfile.objects.count()}")

if __name__ == "__main__":
    main()
