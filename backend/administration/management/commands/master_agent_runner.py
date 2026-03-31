import time
import subprocess
from django.core.management.base import BaseCommand
from django.utils import timezone
from backend.student.models import AttendanceMonitoringLog, FeeMonitoringLog

class Command(BaseCommand):
    help = 'DEPLOYMENT READY: Master runner for all autonomous agentic tasks. Run this as a background process.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Master Agent Runner Started (Deployment Mode)"))
        
        while True:
            try:
                # 1. Assignment Reminders (Every Hour)
                self.stdout.write(f"[{timezone.now()}] Checking assignments...")
                subprocess.run(['python', 'manage.py', 'assignment_reminder_agent'])

                # 2. Attendance (15 Days)
                latest_att = AttendanceMonitoringLog.objects.order_by('-date_performed').first()
                if not latest_att or (timezone.now() - latest_att.date_performed).days >= 15:
                    self.stdout.write(f"[{timezone.now()}] Running periodic attendance audit...")
                    subprocess.run(['python', 'manage.py', 'attendance_agent'])

                # 3. Fees (7 Days)
                latest_fee = FeeMonitoringLog.objects.order_by('-date_performed').first()
                if not latest_fee or (timezone.now() - latest_fee.date_performed).days >= 7:
                    self.stdout.write(f"[{timezone.now()}] Running periodic fee audit...")
                    subprocess.run(['python', 'manage.py', 'fee_agent'])

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error in master runner cycle: {str(e)}"))

            self.stdout.write(f"[{timezone.now()}] Cycle complete. Sleeping for 1 hour...")
            # Sleep for 1 hour
            time.sleep(3600)
