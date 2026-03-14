import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import StudentProfile, Enrollment

def main():
    print("Updating all students to Batch 2023 and 6th Semester...")
    
    # Update StudentProfile batch year
    updated_profiles = StudentProfile.objects.update(batch_year=2023)
    print(f"Updated {updated_profiles} student profiles to Batch 2023.")
    
    # Update Enrollments to 6th Semester
    updated_enrollments = Enrollment.objects.all().update(semester='6th Semester')
    print(f"Updated {updated_enrollments} enrollment records to 6th Semester.")
    
    # Verify properties
    sample = StudentProfile.objects.first()
    if sample:
        print(f"\nVerification for {sample.user.name}:")
        print(f"Batch: {sample.batch_year}")
        print(f"Current Semester (calculated): {sample.current_semester}")
        print(f"Current Year (calculated): {sample.current_year}")

if __name__ == "__main__":
    main()
