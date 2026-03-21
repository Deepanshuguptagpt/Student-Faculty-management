import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from backend.faculty.models import Assignment, AssignmentSubmission, AssignmentReminderLog
from backend.student.models import Enrollment, StudentProfile

class Command(BaseCommand):
    help = 'Sends reminder emails for upcoming assignments'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force send even if not in time window (for testing)')

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Running Assignment Reminder Agent at {now}")

        # 1. Get all assignments that are not yet due
        active_assignments = Assignment.objects.filter(due_datetime__gt=now)

        for assignment in active_assignments:
            # 2. Find students who SHOULD have submitted but haven't
            # These are students enrolled in the same course and branch
            enrolled_students = StudentProfile.objects.filter(
                branch=assignment.branch,
                enrollments__course=assignment.course
            ).distinct()

            for student in enrolled_students:
                # 3. Check if they already submitted
                if AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists():
                    continue

                # 4. Determine if any reminder stage is reached
                reminder_type = self.get_due_reminder_type(assignment, student, now, options['force'])
                
                if reminder_type:
                    self.send_reminder_email(assignment, student, reminder_type)
                    # Log the reminder
                    AssignmentReminderLog.objects.create(
                        assignment=assignment,
                        student=student,
                        reminder_type=reminder_type
                    )
                    self.stdout.write(self.style.SUCCESS(f"Sent {reminder_type} reminder to {student.user.email} for {assignment.title}"))

    def get_due_reminder_type(self, assignment, student, now, force):
        """
        Calculates if a reminder is due based on the user's requirements.
        """
        created_at = assignment.created_at
        due_at = assignment.due_datetime
        total_duration = due_at - created_at
        time_passed = now - created_at
        remaining_time = due_at - now

        if total_duration.total_seconds() <= 0:
            return None

        # Helper to check if log exists
        def already_sent(rtype):
            return AssignmentReminderLog.objects.filter(assignment=assignment, student=student, reminder_type=rtype).exists()

        # Stages
        # 1. 50% duration
        if time_passed >= total_duration * 0.5 and not already_sent('50'):
            return '50'
        
        # 2. 75% duration
        if time_passed >= total_duration * 0.75 and not already_sent('75'):
            return '75'
        
        # 3. 90% duration
        if time_passed >= total_duration * 0.9 and not already_sent('90'):
            return '90'

        # 4. Submission Day (same day as deadline)
        if now.date() == due_at.date():
            # Morning (8:00 AM)
            if now.hour >= 8 and not already_sent('day_morning'):
                return 'day_morning'
            
            # Evening (6:00 PM)
            if now.hour >= 18 and not already_sent('day_evening'):
                return 'day_evening'
            
            # 3 hours before deadline
            if remaining_time <= datetime.timedelta(hours=3) and not already_sent('final'):
                return 'final'

        if force:
            return '50' # Default for force test

        return None

    def send_reminder_email(self, assignment, student, reminder_type):
        subject = f"Reminder: Assignment '{assignment.title}' is due soon! - Academiq"
        
        reminder_labels = {
            '50': "Time is halfway through! You should start working on your assignment.",
            '75': "The deadline is approaching fast (75% time completed).",
            '90': "URGENT: Only 10% of the scheduled time is remaining!",
            'day_morning': "Final Day Reminder: Today is the last day to submit your assignment.",
            'day_evening': "Evening Reminder: Just a few hours left for your submission.",
            'final': "CRITICAL: The deadline is in less than 3 hours! Submit now.",
        }

        message = f"""
Dear {student.user.name},

This is a reminder from Academiq regarding your assignment submission.

Assignment: {assignment.title}
Course: {assignment.course.name} ({assignment.course.code})
Deadline: {assignment.due_datetime.strftime('%B %d, %Y at %I:%M %p')}

Status: {reminder_labels.get(reminder_type, 'Your assignment is pending.')}

Please ensure you submit your work on time to avoid any academic penalties.

You can submit your assignment by logging into the Academiq portal.

Best Regards,
Academiq AI Agent
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [student.user.email],
            fail_silently=False,
        )
