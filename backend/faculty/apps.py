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
        # We've moved automation to a dedicated worker command: master_agent_runner
        # Run 'python manage.py master_agent_runner' in a separate process for deployment.
        pass
