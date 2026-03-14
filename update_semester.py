import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import StudentProfile, Enrollment, FeeRecord, AcademicRecord

def update_students():
    # 1. Update batch_year for all students to 2023
    # In March 2026, batch_year=2023 gives (2026-2023)*2 = 6th semester.
    profiles_updated = StudentProfile.objects.all().update(batch_year=2023)
    print(f"Updated {profiles_updated} StudentProfiles to batch_year=2023 (3rd Year, 6th Sem).")

    # 2. Update enrollments to 6th Semester
    enrollments_updated = Enrollment.objects.all().update(semester='6th Semester')
    print(f"Updated {enrollments_updated} Enrollments to 6th Semester.")

    # 3. Update FeeRecords to 6th Semester
    fees_updated = FeeRecord.objects.all().update(semester='6th Semester')
    print(f"Updated {fees_updated} FeeRecords to 6th Semester.")

    # 4. Update AcademicRecords to 6th Semester
    academic_updated = AcademicRecord.objects.all().update(semester='6th Semester')
    print(f"Updated {academic_updated} AcademicRecords to 6th Semester.")

if __name__ == '__main__':
    update_students()
