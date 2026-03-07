import os
import django
from datetime import date, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile, Course, Enrollment, Attendance, FeeRecord, AcademicRecord
from backend.administration.models import FacultyProfile

def seed_data():
    print("Seeding test data...")
    
    # 1. Ensure user exists
    user, created = User.objects.get_or_create(
        email='student@test.com',
        defaults={
            'name': 'Test Student', 
            'role': 'student', 
            'password': 'password123'
        }
    )
    if created:
        print("Created test user: student@test.com")

    admin, created = User.objects.get_or_create(
        email='admin@example.com',
        defaults={
            'name': 'System Admin', 
            'role': 'admin', 
            'password': 'ADMIN'
        }
    )
    if created:
        print("Created admin user: admin@example.com")

    # 2. Create Student Profile
    profile, created = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            'enrollment_number': 'ENR2026001',
            'batch_year': 2026,
            'contact_number': '+1234567890',
            'address': '123 University St, Tech City',
            'date_of_birth': date(2004, 5, 15)
        }
    )

    # 3. Create Courses
    cs101, _ = Course.objects.get_or_create(code='CS101', defaults={'name': 'Introduction to Computer Science', 'credits': 4})
    mt201, _ = Course.objects.get_or_create(code='MT201', defaults={'name': 'Calculus II', 'credits': 3})
    phy102, _ = Course.objects.get_or_create(code='PHY102', defaults={'name': 'Physics for Engineers', 'credits': 4})

    # 4. Enroll Student
    Enrollment.objects.get_or_create(student=profile, course=cs101, semester='Fall 2026')
    Enrollment.objects.get_or_create(student=profile, course=mt201, semester='Fall 2026')
    Enrollment.objects.get_or_create(student=profile, course=phy102, semester='Fall 2026')

    # 5. Add Attendance (Some dates in the past)
    today = date.today()
    for i in range(5):
        eval_date = today - timedelta(days=i)
        Attendance.objects.get_or_create(student=profile, course=cs101, date=eval_date, defaults={'status': 'Present' if i % 4 != 0 else 'Absent'})
        Attendance.objects.get_or_create(student=profile, course=mt201, date=eval_date, defaults={'status': 'Present'})

    # 6. Add Fees
    FeeRecord.objects.get_or_create(student=profile, semester='Fall 2026', defaults={'amount_due': 5000.00, 'amount_paid': 2500.00, 'due_date': date(2026, 8, 1), 'status': 'Pending'})
    FeeRecord.objects.get_or_create(student=profile, semester='Spring 2026', defaults={'amount_due': 4800.00, 'amount_paid': 4800.00, 'due_date': date(2026, 1, 15), 'status': 'Paid'})

    # 7. Add Academic Records
    AcademicRecord.objects.get_or_create(student=profile, course=cs101, semester='Fall 2026', defaults={'grade': 'B+', 'marks': 87.5})
    AcademicRecord.objects.get_or_create(student=profile, course=mt201, semester='Fall 2026', defaults={'grade': 'A', 'marks': 92.0})

    # 8. Add Faculty
    prof1, _ = User.objects.get_or_create(email='prof.smith@univ.edu', defaults={'name': 'Dr. Robert Smith', 'role': 'faculty', 'password': 'password123'})
    prof2, _ = User.objects.get_or_create(email='prof.doe@univ.edu', defaults={'name': 'Prof. Jane Doe', 'role': 'faculty', 'password': 'password123'})

    FacultyProfile.objects.get_or_create(user=prof1, defaults={'employee_id': 'FAC001', 'department': 'Computer Science', 'designation': 'Professor', 'contact_number': '+0987654321'})
    FacultyProfile.objects.get_or_create(user=prof2, defaults={'employee_id': 'FAC002', 'department': 'Physics', 'designation': 'Assistant Professor', 'contact_number': '+1122334455'})

    print("Data seeding complete.")

if __name__ == "__main__":
    seed_data()
