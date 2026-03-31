import datetime
import pandas as pd
from io import BytesIO
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from backend.faculty.models import Assignment, AssignmentSubmission, FacultyAssignmentReportLog
from backend.student.models import StudentProfile
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_assistant.utils import key_rotator

class Command(BaseCommand):
    help = 'Sends assignment submission status reports to faculty'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force send milestones for testing')

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Running Faculty Assignment Report Agent at {now}")

        # 1. Get all assignments
        assignments = Assignment.objects.all()

        for assignment in assignments:
            # 2. Calculate Milestone Logic
            report_stage = self.get_due_report_stage(assignment, now, options['force'])
            
            if report_stage:
                self.send_faculty_report(assignment, report_stage)
                
                # Log the report
                FacultyAssignmentReportLog.objects.get_or_create(
                    assignment=assignment,
                    faculty=assignment.faculty,
                    report_stage=report_stage
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Sent {report_stage} report to {assignment.faculty.user.email} for '{assignment.title}'"
                ))

    def get_due_report_stage(self, assignment, now, force):
        created_at = assignment.created_at
        due_at = assignment.due_datetime

        if not due_at:
            return None

        # Check if log already exists
        def already_sent(stage):
            return FacultyAssignmentReportLog.objects.filter(
                assignment=assignment, 
                faculty=assignment.faculty, 
                report_stage=stage
            ).exists()

        # --- A. Final Deadline Report ---
        if now >= due_at:
            if not already_sent('final'):
                return 'final'
            return None

        # --- B. Milestones (50, 75, 90) ---
        total_duration = due_at - created_at
        time_passed = now - created_at

        if total_duration.total_seconds() <= 0:
            return None

        # Milestones progress
        if time_passed >= total_duration * 0.9 and not already_sent('90'):
            return '90'
        if time_passed >= total_duration * 0.75 and not already_sent('75'):
            return '75'
        if time_passed >= total_duration * 0.5 and not already_sent('50'):
            return '50'

        if force and not already_sent('50'):
            return '50'

        return None

    def send_faculty_report(self, assignment, stage):
        faculty_email = assignment.faculty.user.email
        faculty_name = assignment.faculty.user.name
        
        # Calculate stats
        enrolled_students = StudentProfile.objects.filter(
            branch=assignment.branch,
            enrollments__course=assignment.course
        ).distinct()
        
        total_count = enrolled_students.count()
        submissions = AssignmentSubmission.objects.filter(assignment=assignment)
        submitted_count = submissions.count()
        pending_count = total_count - submitted_count
        
        stage_labels = {
            '50': "50% Milestone reached",
            '75': "75% Milestone reached",
            '90': "90% Milestone (Final Warning)",
            'final': "Final Deadline Status"
        }
        
        stage_desc = stage_labels.get(stage, "Status Update")

        # 1. Final Report with Excel Attachment
        if stage == 'final':
            self.send_final_report_with_excel(assignment, enrolled_students, submissions, faculty_email, faculty_name)
            return

        # 2. Milestone Summary Email (Use AI for summary)
        api_key = key_rotator.get_current_key()
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key) if api_key else ChatGoogleGenerativeAI(model="gemini-2.5-flash")

        summary_prompt = f"""You are the Academiq AI Assistant. Write a brief status report to a faculty member about their assignment.
Faculty Name: {faculty_name}
Assignment: {assignment.title}
Course: {assignment.course.name}
Total Students: {total_count}
Submitted: {submitted_count}
Pending: {pending_count}
Stage: {stage_desc}

Provide 1-2 actionable insights (e.g., if submission is low, suggest a reminder). Keep it to 3 sentences max. Do NOT include a subject line."""

        try:
            response = llm.invoke([
                SystemMessage(content="You are a helpful academic auditor."),
                HumanMessage(content=summary_prompt)
            ])
            ai_insight = response.content.strip()
        except:
            ai_insight = f"Current stats: {submitted_count}/{total_count} submitted. {pending_count} students are still pending."

        email_body = f"""Dear {faculty_name},

This is an automated status update for your assignment '{assignment.title}' (Stage: {stage_desc}).

Status Overview:
- Total Enrolled: {total_count}
- Submissions: {submitted_count}
- Remaining: {pending_count}

AI Insights:
{ai_insight}

Regards,
Academiq AI Agent
"""

        send_mail(
            f"Assignment Status Update: {assignment.title} ({stage_desc})",
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            [faculty_email],
            fail_silently=False,
        )

    def send_final_report_with_excel(self, assignment, enrolled_students, submissions, faculty_email, faculty_name):
        # Generate Data for Excel
        submitted_ids = set(submissions.values_list('student_id', flat=True))
        data = []
        for s in enrolled_students:
            status = "Submitted" if s.id in submitted_ids else "PENDING"
            sub_date = ""
            if s.id in submitted_ids:
                sub = submissions.filter(student=s).first()
                sub_date = sub.submitted_at.strftime('%Y-%m-%d %H:%M') if sub else ""
            
            data.append({
                'Student Name': s.user.name,
                'Enrollment Number': s.enrollment_number,
                'Status': status,
                'Submission Date': sub_date
            })

        df = pd.DataFrame(data)
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Submission Status')
        excel_buffer.seek(0)

        email_body = f"""Dear {faculty_name},

The deadline for your assignment '{assignment.title}' has been reached.

Please find attached the final submission report in Excel format. This report includes a list of all students and their submission status.

Summary:
- Total Students: {len(data)}
- Final Submissions: {submissions.count()}
- Missing Submissions: {len(data) - submissions.count()}

Regards,
Academiq AI Agent
"""

        email = EmailMessage(
            subject=f"FINAL Assignment Report: {assignment.title}",
            body=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[faculty_email],
        )
        email.attach(f"Final_Report_{assignment.title.replace(' ', '_')}.xlsx", excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        email.send(fail_silently=False)
