import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile, Course, Enrollment, Attendance, FeeRecord, AcademicRecord, AttendanceMonitoringLog, AttendanceIntervention
from backend.faculty.models import FacultyProfile, Department

def clear_all_data():
    print("Starting to clear all project data...")
    
    # Order matters due to cascades, but Django handles most of it.
    # We clear the leaf nodes first or use bulk delete.
    
    print("Deleting Attendance Monitoring Logs & Interventions...")
    AttendanceIntervention.objects.all().delete()
    AttendanceMonitoringLog.objects.all().delete()
    
    print("Deleting Academic & Fee Records...")
    AcademicRecord.objects.all().delete()
    FeeRecord.objects.all().delete()
    
    print("Deleting Attendance & Enrollments...")
    Attendance.objects.all().delete()
    Enrollment.objects.all().delete()
    
    print("Deleting Profiles...")
    StudentProfile.objects.all().delete()
    FacultyProfile.objects.all().delete()
    
    print("Deleting Courses & Departments...")
    Course.objects.all().delete()
    Department.objects.all().delete()
    
    # Delete users except for the ones likely to be real admins
    # Usually we keep the user who is logged in or designated as admin
    print("Deleting Users (keeping admin@example.com)...")
    initial_count = User.objects.count()
    User.objects.exclude(email='admin@example.com').delete()
    final_count = User.objects.count()
    
    print(f"Data cleared! Users reduced from {initial_count} to {final_count}.")
    print("The system is now in a clean state (ready for fresh imports).")

if __name__ == "__main__":
    clear_all_data()
