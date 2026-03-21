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
                from backend.student.models import AttendanceMonitoringLog
                
                latest = AttendanceMonitoringLog.objects.order_by('-date_performed').first()
                should_run = False
                
                if not latest:
                    should_run = True
                else:
                    days_since = (datetime.now(timezone.utc) - latest.date_performed).days
                    if days_since >= 15:
                        should_run = True
                
                if should_run:
                    # Run the management command
                    subprocess.Popen(['python', 'manage.py', 'attendance_agent'])
                
            except Exception as e:
                # Silently catch errors in the background thread to avoid crashing the server
                pass
            
            # Check once every 12 hours
            time.sleep(12 * 3600)
