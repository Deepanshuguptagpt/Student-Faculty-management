import os
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from backend.student.models import StudentProfile, AttendanceMonitoringLog, AttendanceIntervention
from backend.student.utils import calculate_detailed_attendance
from core.ollama_utils import generate_ollama_insight

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
        
        students = StudentProfile.objects.all()
        log.students_analyzed = students.count()
        
        at_risk_count = 0
        emails_sent = 0
        
        at_risk_data = [] # For coordinator report
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

            # 4. Check Threshold
            if overall_pct < 75.0:
                at_risk_count += 1
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

Your ward's current overall attendance is {overall_pct}%, which is below the minimum required threshold of 75%.

Theory Attendance: {data['global_theory_pct']}%
Practical Attendance: {data['global_practical_pct']}%

Kindly note that improvement in your attendance is mandatory to comply with academic regulations.

Best Regards,
Indore Institute Management Portal
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

                # Add to report data
                at_risk_data.append({
                    'name': student.user.name,
                    'enrollment': student.enrollment_number,
                    'overall': overall_pct,
                    'deficit': round(75.0 - float(overall_pct), 1),
                    'courses': data['course_data']
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

        # 6. Faculty Coordinator Report
        report_log_str = f"Students at risk: {at_risk_count}\n"
        for item in at_risk_data:
            report_log_str += f"- {item['name']} ({item['enrollment']}): {item['overall']}% (Deficit: {item['deficit']}%)\n"
            
        # 7. Generate AI Insights via Ollama
        prompt = f"""
Analyze the following student attendance data for the last 15 days and provide a concise academic summary:
Total students analyzed: {log.students_analyzed}
Students below 75%: {at_risk_count}
Students close to threshold: {len(close_to_threshold_list)}
Lowest attendance: {", ".join(top_lowest)}
Common low-attendance courses: {", ".join(low_perf_courses) if low_perf_courses else "None"}

Provide 3 actionable insights for the Faculty Coordinator {COORDINATOR_NAME}.
        """
        self.stdout.write("Generating AI insights via Ollama...")
        insight = generate_ollama_insight(prompt)
        log.summary_insight = insight
        
        # 8. Send Report to Coordinator
        coordinator_body = f"""
Dear {COORDINATOR_NAME},

Here is the 15-day Attendance Monitoring Report.

Summary:
- Total Students Analyzed: {log.students_analyzed}
- Students at Risk (< 75%): {at_risk_count}
- Notification Emails Sent: {emails_sent}

AI Generated Insights:
{insight}

Detailed List of At-Risk Students:
{report_log_str}

Please take necessary academic actions.

Regards,
Attendance Monitoring Agent
        """
        
        try:
            send_mail(
                '15-Day Attendance Analysis Report',
                coordinator_body,
                'noreply@indoreinstitute.com',
                [COORDINATOR_EMAIL],
                fail_silently=True,
            )
            log.reports_generated += 1
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send coordinator report: {str(e)}"))

        # 9. Update Log
        log.students_at_risk = at_risk_count
        log.emails_sent = emails_sent
        log.reports_generated = 1
        log.save()
        
        self.stdout.write(self.style.SUCCESS(f"Analysis Complete. Found {at_risk_count} students at risk. Log ID: {log.id}"))
        self.stdout.write(f"AI Insight: {insight[:100]}...")
