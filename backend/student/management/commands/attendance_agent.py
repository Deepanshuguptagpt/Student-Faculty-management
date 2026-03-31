import os
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import pandas as pd
from io import BytesIO
from django.core.mail import send_mail, EmailMessage
from backend.student.models import StudentProfile, AttendanceMonitoringLog, AttendanceIntervention
from backend.faculty.models import SectionCoordinator
from backend.student.utils import calculate_detailed_attendance
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_assistant.utils import key_rotator

class Command(BaseCommand):
    help = 'Runs the Agentic AI Attendance Monitor every 15 days'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force analysis even if 15 days haven\'t passed')

    def handle(self, *args, **options):
        self.stdout.write("--- Starting Agentic AI Attendance Monitoring ---")
        
        # 1. Check if it's time to run (every 15 days)
        last_log = AttendanceMonitoringLog.objects.order_by('-date_performed').first()
        if last_log and not options['force']:
            if timezone.now() < last_log.date_performed + timedelta(days=15):
                self.stdout.write(self.style.WARNING(f"Skipping: Last analysis was on {last_log.date_performed}. 15 days have not passed."))
                return

        # 2. Initialize log
        log = AttendanceMonitoringLog.objects.create()
        
        COORDINATOR_EMAIL = "rawatkanak03@gmail.com"
        COORDINATOR_NAME = "Mrs. Sukrati Agrawal"
        
        # USER REQUEST: Only run for AIML-1 section as other sections don't have timetable data yet
        students = StudentProfile.objects.filter(section='AIML-1')
        log.students_analyzed = students.count()
        
        emails_sent = 0
        at_risk_by_section = {} # (branch, section) -> list of student data
        lowest_attendance_list = []
        close_to_threshold_list = []
        course_performance = {} # track course-wise attendance across all students
        
        for student in students:
            # 3. Calculate attendance using existing logic
            data = calculate_detailed_attendance(student)
            overall_pct = data['global_overall_pct']
            
            # Update course performance metrics
            for cd in data['course_data']:
                code = cd['base_code']
                if code not in course_performance:
                    course_performance[code] = {'total': 0, 'present': 0}
                course_performance[code]['total'] += cd['theory']['total'] + cd['practical']['total']
                course_performance[code]['present'] += cd['theory']['present'] + cd['practical']['present']

            # 4. Check Threshold (Updated to 85.0% as per USER request)
            if overall_pct < 85.0:
                student.attendance_risk = True
                student.save()
                
                # Create intervention
                intervention = AttendanceIntervention.objects.create(
                    log=log,
                    student=student,
                    overall_attendance=overall_pct
                )
                
                # 5. Automated Notification (Email to Parent)
                target_email = student.parent_email
                
                if not target_email:
                    # Fallback or skip if no parent email
                     intervention.save()
                     continue
                
                email_body = f"""
Dear Parent/Guardian of {student.user.name},

Enrollment Number: {student.enrollment_number}
Branch: {student.branch}
Semester: {student.current_semester}

Your ward's current overall attendance is {overall_pct}%, which is below the minimum required threshold of 85%.

Theory Attendance: {data['global_theory_pct']}%
Practical Attendance: {data['global_practical_pct']}%

Kindly note that improvement in your attendance is mandatory to comply with academic regulations.

Best Regards,
Academiq Management Portal
                """
                
                try:
                    # In a real scenario, we'd send_mail. For now, we log and increment.
                    # self.stdout.write(f"Sending alert to {target_email}...")
                    send_mail(
                        'Attendance Warning: Action Required',
                        email_body,
                        'noreply@indoreinstitute.com',
                        [target_email],
                        fail_silently=True,
                    )
                    intervention.notification_sent = True
                    intervention.date_sent = timezone.now()
                    intervention.save()
                    emails_sent += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {target_email}: {str(e)}"))

                # Add to section-wise report data
                key = (student.branch, student.section)
                if key not in at_risk_by_section:
                    at_risk_by_section[key] = []
                    
                at_risk_by_section[key].append({
                    'Name': student.user.name,
                    'Enrollment': student.enrollment_number,
                    'Branch': student.branch,
                    'Section': student.section,
                    'Overall Attendance %': overall_pct,
                    'Deficit %': round(85.0 - float(overall_pct), 1),
                    'Parent Email': student.parent_email
                })
            else:
                student.attendance_risk = False
                student.save()
                
                if overall_pct >= 75.0 and overall_pct < 80.0:
                    close_to_threshold_list.append(f"{student.user.name} ({overall_pct}%)")

            lowest_attendance_list.append((student.user.name, overall_pct))

        # Sort and filter for insights
        lowest_attendance_list.sort(key=lambda x: x[1])
        top_lowest = [f"{n}: {p}%" for n, p in lowest_attendance_list[:5]]
        
        low_perf_courses = []
        for code, stats in course_performance.items():
            pct = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
            if pct < 70:
                low_perf_courses.append(f"{code} ({round(pct, 1)}%)")

        # 6. Send Section-Specific Reports to Coordinators
        total_at_risk = 0
        for (branch, section), students_list in at_risk_by_section.items():
            total_at_risk += len(students_list)
            
            # Find coordinator
            coord = SectionCoordinator.objects.filter(branch=branch, section=section).first()
            coord_name = coord.faculty.user.name if coord else "Coordinator"
            
            # USER REQUEST: Use this specific email for coordinators
            coord_email = "rawatkanak03@gmail.com"
            
            # 6a. Generate Excel Attachment
            df = pd.DataFrame(students_list)
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='At Risk Students')
            excel_buffer.seek(0)
            
            # 6b. Generate Section-wise AI Insights using Gemini
            api_key = key_rotator.get_current_key()
            llm_kwargs = {"model": "gemini-2.5-flash", "temperature": 0.7}
            if api_key:
                llm_kwargs["google_api_key"] = api_key
            llm = ChatGoogleGenerativeAI(**llm_kwargs)

            section_prompt = f"""You are the Academiq Attendance Auditor. Analyze this data for Section {section}, Branch {branch}:
Students at risk: {len(students_list)}
Top 3 lowest attendance in this section: {[f"{s['Name']} ({s['Overall Attendance %']}%)" for s in students_list[:3]]}

Provide 2-3 quick, actionable, professional insights for Coordinator {coord_name}. Ensure the tone is analytical yet supportive. Keep it under 100 words."""
            
            try:
                response = llm.invoke([
                    SystemMessage(content="You are an expert academic data analyst."),
                    HumanMessage(content=section_prompt)
                ])
                section_insight = response.content.strip()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Gemini insight generation failed for section {section}: {e}"))
                section_insight = "Monitoring indicates several students are below the mandatory threshold. Immediate counseling is recommended."
            
            # 6c. Send Email with Attachment
            email_body = f"""
Dear {coord_name},

This is the automated attendance monitoring report for {branch} - {section}.

Summary:
- Section: {section}
- Students below 75%: {len(students_list)}

AI Insights for your section:
{section_insight}

Please find the attached Excel file for the complete list of at-risk students and their details.

Regards,
Academiq AI Agent
            """
            
            try:
                email = EmailMessage(
                    subject=f'Attendance Report: {branch} - {section}',
                    body=email_body,
                    from_email='noreply@indoreinstitute.com',
                    to=[coord_email],
                )
                email.attach(f'At_Risk_Students_{section}.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                email.send(fail_silently=True)
                log.reports_generated += 1
                self.stdout.write(self.style.SUCCESS(f"Sent report for {section} to {coord_email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send report for {section}: {str(e)}"))

        # 7. Global AI Summary for the Log
        global_prompt = f"""Summarize the overall attendance status for {log.students_analyzed} students. 
Total at risk (<85%): {total_at_risk}.
Write a single, high-level summary sentence for the administration dashboard."""
        
        try:
            response = llm.invoke([
                SystemMessage(content="You are an academic administrator."),
                HumanMessage(content=global_prompt)
            ])
            log.summary_insight = response.content.strip()
        except:
            log.summary_insight = f"Analysis complete for {log.students_analyzed} students. {total_at_risk} identified as at-risk."

        log.students_at_risk = total_at_risk

        # 9. Update Log
        log.students_at_risk = total_at_risk
        log.emails_sent = emails_sent
        log.save()
        
        self.stdout.write(self.style.SUCCESS(f"Analysis Complete. Found {total_at_risk} students at risk. Log ID: {log.id}"))
        self.stdout.write(f"AI Insight: {log.summary_insight[:100]}...")
