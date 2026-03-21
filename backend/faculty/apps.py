from django.apps import AppConfig
import threading
import time
import subprocess
import os
from datetime import datetime, timezone, timedelta

class FacultyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.faculty'

    def ready(self):
        # Only run inside the main process, not the reloader
        if os.environ.get('RUN_MAIN') == 'true':
            threading.Thread(target=self.start_automation_scheduler, daemon=True).start()

    def start_automation_scheduler(self):
        # Wait for system to settle
        time.sleep(30)
        
        while True:
            try:
                from django.utils import timezone
                # 1. Assignment Reminders (Check every run)
                subprocess.Popen(['python', 'manage.py', 'assignment_reminder_agent'])

                # 2. Attendance Agent (Check every 15 days)
                from backend.student.models import AttendanceMonitoringLog
                latest = AttendanceMonitoringLog.objects.order_by('-date_performed').first()
                should_run_attendance = False
                
                if not latest:
                    should_run_attendance = True
                else:
                    days_since = (timezone.now() - latest.date_performed).days
                    if days_since >= 15:
                        should_run_attendance = True
                
                if should_run_attendance:
                    subprocess.Popen(['python', 'manage.py', 'attendance_agent'])
                
            except Exception as e:
                # Silently catch errors in background
                pass
            
            # Check once every hour for reminders
            time.sleep(3600)
