
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
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_assistant.utils import key_rotator

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
        pending_by_section = {} # (branch, section) -> list of student data
        
        for student in students:
            # 3. Find pending/unpaid records for this student
            # We include both 'Pending' and 'Overdue' as both represent unpaid fees
            unpaid_records = FeeRecord.objects.filter(
                student=student,
                status__in=['Pending', 'Overdue']
            )
            
            if unpaid_records.exists():
                total_unpaid = sum(record.remaining_amount for record in unpaid_records)
                
                # Create intervention log entry
                intervention = FeeIntervention.objects.create(
                    log=log,
                    student=student,
                    amount_overdue=total_unpaid # This field label in model is 'overdue' but represents total unpaid
                )
                
                # 4. Automated Notification specifically to STUDENT as requested
                student_email = student.user.email
                
                if not student_email:
                     intervention.save()
                     continue
                
                unpaid_details = "\n".join([f"- {r.semester}: ₹{r.remaining_amount} {'(Pending)' if r.status == 'Pending' else '(Overdue)'}" for r in unpaid_records])
                
                email_body = f"""
Dear {student.user.name},

Enrollment Number: {student.enrollment_number}
Branch: {student.branch}
Section: {student.section}

Our records indicate that your fees for the following semesters are still unpaid/pending:

{unpaid_details}

Total Outstanding Amount: ₹{total_unpaid}

Kindly ensure the payment is made at the earliest. If you have already paid, please ignore this email or provide the transaction details to the accounts department.

Regards,
Fee Management Agent
Academiq Management Portal
                """
                
                try:
                    send_mail(
                        'Fee Payment Reminder - Academiq',
                        email_body,
                        'accounts@indoreinstitute.com',
                        [student_email],
                        fail_silently=True,
                    )
                    intervention.notification_sent = True
                    intervention.date_sent = timezone.now()
                    intervention.save()
                    emails_sent += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {student_email}: {str(e)}"))

                # Add to section-wise report data for coordinator
                key = (student.branch, student.section)
                if key not in pending_by_section:
                    pending_by_section[key] = []
                    
                pending_by_section[key].append({
                    'Name': student.user.name,
                    'Enrollment': student.enrollment_number,
                    'Branch': student.branch,
                    'Section': student.section,
                    'Unpaid Amount': float(total_unpaid),
                    'Fee Details': unpaid_details.replace('\n', ' | '),
                    'Email': student.user.email
                })

        # 5. Send Section-Specific Reports to Coordinators with Excel Attachment
        total_pending_count = 0
        for (branch, section), students_list in pending_by_section.items():
            total_pending_count += len(students_list)
            
            # Find coordinator for this specific section
            coord = SectionCoordinator.objects.filter(branch=branch, section=section).first()
            if not coord:
                continue
                
            coord_name = coord.faculty.user.name
            coord_email = coord.faculty.user.email
            
            # 5a. Generate Excel Attachment in memory
            df = pd.DataFrame(students_list)
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Pending Fee Students')
            excel_buffer.seek(0)
            
            # 5b. Generate Section-wise AI Insight using Gemini
            api_key = key_rotator.get_current_key()
            llm_kwargs = {"model": "gemini-2.5-flash", "temperature": 0.7}
            if api_key:
                llm_kwargs["google_api_key"] = api_key
            llm = ChatGoogleGenerativeAI(**llm_kwargs)

            prompt = f"""You are the Academiq Fee Auditor. Analyze this data for Section {section}, Branch {branch}:
Students with unpaid fees: {len(students_list)}
Top 3 highest outstanding amounts: {[f"{s['Name']} (₹{s['Unpaid Amount']})" for s in students_list[:3]]}

Provide a short, professional action nudge for Coordinator {coord_name} to help recover these dues. Keep it under 60 words."""
            
            try:
                response = llm.invoke([
                    SystemMessage(content="You are a financial academic advisor."),
                    HumanMessage(content=prompt)
                ])
                insight = response.content.strip()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Gemini insight generation failed for fee report (section {section}): {e}"))
                insight = "High number of pending dues detected. Immediate follow-up with these students is advised."
            
            # 5c. Send Email with Attachment
            email_body = f"""
Dear {coord_name},

Attached is the list of students in your section ({branch} - {section}) who have pending fee dues.

Summary:
- Students with Pending Fees: {len(students_list)}
- Action Nudge: {insight}

Kindly follow up with these students to ensure timely fee clearance.

Regards,
Accounts Department
            """
            
            try:
                email = EmailMessage(
                    subject=f'Fee Status Report: {branch} - {section}',
                    body=email_body,
                    from_email='accounts@indoreinstitute.com',
                    to=[coord_email],
                )
                email.attach(f'Pending_Fees_{section}_{branch}.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                email.send(fail_silently=True)
                log.reports_generated += 1
                self.stdout.write(self.style.SUCCESS(f"Sent excel report for {section} to coordinator {coord_email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send report for {section}: {str(e)}"))

        # 6. Global AI Summary for the Log
        global_prompt = f"Fee audit complete for {log.students_analyzed} students. Found {total_pending_count} students with pending dues. Summarize the financial risk in one short sentence."
        
        try:
            response = llm.invoke([
                SystemMessage(content="You are a senior university administrator."),
                HumanMessage(content=global_prompt)
            ])
            log.summary_insight = response.content.strip()
        except:
            log.summary_insight = f"Audit complete. {total_pending_count} students have outstanding fee balances."
        log.overdue_students = total_pending_count
        log.emails_sent = emails_sent
        log.save()
        
        self.stdout.write(self.style.SUCCESS(f"Fee Monitoring Complete. Found {total_overdue_count} students with overdue fees. Log ID: {log.id}"))

