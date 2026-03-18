
import os
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import pandas as pd
from io import BytesIO
from django.core.mail import send_mail, EmailMessage
from backend.student.models import StudentProfile, FeeRecord, FeeMonitoringLog, FeeIntervention
from backend.faculty.models import SectionCoordinator
from core.ollama_utils import generate_ollama_insight

class Command(BaseCommand):
    help = 'Runs the Agentic AI Fee Management Monitor weekly'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force analysis even if 7 days haven\'t passed')

    def handle(self, *args, **options):
        self.stdout.write("--- Starting Agentic AI Fee Management Monitoring ---")
        
        # 1. Check if it's time to run (every 7 days)
        last_log = FeeMonitoringLog.objects.order_by('-date_performed').first()
        if last_log and not options['force']:
            if timezone.now() < last_log.date_performed + timedelta(days=7):
                self.stdout.write(self.style.WARNING(f"Skipping: Last analysis was on {last_log.date_performed}. 7 days have not passed."))
                return

        # 2. Initialize log
        log = FeeMonitoringLog.objects.create()
        
        # Target all students as per request
        students = StudentProfile.objects.all()
        log.students_analyzed = students.count()
        
        emails_sent = 0
        overdue_by_section = {} # (branch, section) -> list of student data
        
        today = timezone.now().date()
        
        for student in students:
            # 3. Find overdue records for this student
            overdue_records = FeeRecord.objects.filter(
                student=student,
                status__in=['Pending', 'Overdue'],
                due_date__lt=today
            )
            
            if overdue_records.exists():
                total_overdue = sum(record.remaining_amount for record in overdue_records)
                
                # Create intervention
                intervention = FeeIntervention.objects.create(
                    log=log,
                    student=student,
                    amount_overdue=total_overdue
                )
                
                # 4. Automated Notification to Student/Parent
                target_email = student.user.email  # Sending to student's email as well
                parent_email = student.parent_email
                
                recipients = []
                if target_email: recipients.append(target_email)
                if parent_email: recipients.append(parent_email)
                
                if not recipients:
                     intervention.save()
                     continue
                
                overdue_details = "\n".join([f"- {r.semester}: ₹{r.remaining_amount} (Due: {r.due_date})" for r in overdue_records])
                
                email_body = f"""
Dear {student.user.name},

Enrollment Number: {student.enrollment_number}
Branch: {student.branch}
Section: {student.section}

Our records indicate that your fees for the following semesters are still outstanding:

{overdue_details}

Total Outstanding Amount: ₹{total_overdue}

Kindly ensure the payment is made at the earliest to avoid any inconvenience. If you have already paid, please ignore this email or provide the transaction details to the accounts department.

Best Regards,
Accounts Department
Indore Institute Management Portal
                """
                
                try:
                    send_mail(
                        'Urgent: Fee Payment Reminder',
                        email_body,
                        'accounts@indoreinstitute.com',
                        recipients,
                        fail_silently=True,
                    )
                    intervention.notification_sent = True
                    intervention.date_sent = timezone.now()
                    intervention.save()
                    emails_sent += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {recipients}: {str(e)}"))

                # Add to section-wise report data for coordinator
                key = (student.branch, student.section)
                if key not in overdue_by_section:
                    overdue_by_section[key] = []
                    
                overdue_by_section[key].append({
                    'Name': student.user.name,
                    'Enrollment': student.enrollment_number,
                    'Branch': student.branch,
                    'Section': student.section,
                    'Overdue Amount': float(total_overdue),
                    'Details': overdue_details.replace('\n', ' | '),
                    'Student Email': student.user.email,
                    'Parent Email': student.parent_email
                })

        # 5. Send Section-Specific Reports to Coordinators
        total_overdue_count = 0
        for (branch, section), students_list in overdue_by_section.items():
            total_overdue_count += len(students_list)
            
            # Find coordinator
            coord = SectionCoordinator.objects.filter(branch=branch, section=section).first()
            if not coord:
                # If no coordinator, we skip for this section or could send to admin
                # The user said "coordinator will recieve the list... otherwise not"
                continue
                
            coord_name = coord.faculty.user.name
            coord_email = coord.faculty.user.email
            
            # 5a. Generate Excel Attachment
            df = pd.DataFrame(students_list)
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Unpaid Fees Students')
            excel_buffer.seek(0)
            
            # 5b. Generate AI Insights (Optional)
            section_prompt = f"Summarize the fee status for {section} of {branch}. {len(students_list)} students have unpaid fees totaling a significant amount. Provide a one-sentence nudge for the coordinator {coord_name}."
            section_insight = generate_ollama_insight(section_prompt)
            
            # 5c. Send Email with Attachment
            email_body = f"""
Dear {coord_name},

This is the weekly fee status report for your section: {branch} - {section}.

Summary:
- Total Students with Overdue Fees: {len(students_list)}
- AI Nudge: {section_insight}

Please find attached the list of students who have not paid their fees even after the last date of submission. Kindly follow up with them to ensure timely clearance of dues.

Regards,
Fee Management Agent
            """
            
            try:
                email = EmailMessage(
                    subject=f'Fee Status Report: {branch} - {section}',
                    body=email_body,
                    from_email='accounts@indoreinstitute.com',
                    to=[coord_email],
                )
                email.attach(f'Overdue_Fees_{section}.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                email.send(fail_silently=True)
                log.reports_generated += 1
                self.stdout.write(self.style.SUCCESS(f"Sent fee report for {section} to {coord_email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send report for {section}: {str(e)}"))

        # 6. Global AI Insights
        global_prompt = f"Fee monitoring complete. {total_overdue_count} students have overdue fees. Provide a summary insight."
        log.summary_insight = generate_ollama_insight(global_prompt)
        log.overdue_students = total_overdue_count
        log.emails_sent = emails_sent
        log.save()
        
        self.stdout.write(self.style.SUCCESS(f"Fee Monitoring Complete. Found {total_overdue_count} students with overdue fees. Log ID: {log.id}"))

