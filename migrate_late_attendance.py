import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import Attendance

def migrate_late_attendance():
    print("Migrating 'Late' attendance records to 'Present'...")
    updated_count = Attendance.objects.filter(status='Late').update(status='Present')
    print(f"Successfully updated {updated_count} records.")

if __name__ == '__main__':
    migrate_late_attendance()
