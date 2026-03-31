"""
Student AI Assistant — Agentic, context-aware.

All tools are scoped to the logged-in student only.
- Attendance: per-course breakdown, lowest course highlighted.
- Assignments: ONLY pending + deadline NOT passed, with missed-history warning.
- Summary: combined academic overview.
Uses LangGraph's create_react_agent (LangChain 1.x compatible).
"""

from datetime import datetime, timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from backend.faculty.models import Assignment, AssignmentSubmission
from backend.student.models import StudentProfile, Attendance, Enrollment, FeeRecord
from backend.student.utils import calculate_detailed_attendance
from ai_assistant.utils import key_rotator


def get_student_agent(student_id):
    api_key = key_rotator.get_current_key()
    llm_kwargs = {"model": "gemini-2.5-flash", "temperature": 0}
    if api_key:  # only pass explicitly if we have a key; otherwise let the library read GOOGLE_API_KEY env var
        llm_kwargs["google_api_key"] = api_key
    llm = ChatGoogleGenerativeAI(**llm_kwargs)

    # ─── Resolve student once ─────────────────────────────────────────────────
    student = StudentProfile.objects.select_related('user').get(id=student_id)
    student_name = student.user.name

    # ─── TOOL 1: Full Attendance Summary ──────────────────────────────────────
    @tool
    def check_my_attendance(dummy: str = "") -> str:
        """
        Get a full attendance summary: overall percentage, theory vs practical,
        and per-course breakdown sorted from lowest to highest.
        The lowest-attendance course is highlighted with a warning.
        Input: any string (ignored).
        Use for: 'What is my attendance?', 'Am I at risk?',
        'Which subject am I lowest in?', 'Show my attendance'.
        """
        try:
            data = calculate_detailed_attendance(student)
        except Exception as e:
            return f"Error fetching attendance: {str(e)}"

        overall = data['global_overall_pct']
        theory = data['global_theory_pct']
        practical = data['global_practical_pct']
        courses = sorted(data['course_data'], key=lambda c: c['percentage'])

        lines = [
            f"Attendance Summary for {student_name}",
            f"Overall: {overall:.1f}%  (Theory: {theory:.1f}%, Practical: {practical:.1f}%)",
            "",
            "Per-Course Breakdown (lowest first):",
        ]

        for c in courses:
            pct = c['percentage']
            total = c['total_all']
            present = c['present_all']
            flag = "[LOW]" if pct < 65 else ("[WARN]" if pct < 75 else "[OK]")
            lines.append(
                f"  {flag} {c['base_code']} - {c['name']}: "
                f"{pct:.1f}% ({present}/{total})"
            )

        if courses:
            worst = courses[0]
            if worst['percentage'] < 75:
                lines += [
                    "",
                    f"WARNING: Your lowest course is {worst['base_code']} ({worst['name']}) "
                    f"at {worst['percentage']:.1f}%. Attend more classes to stay above 75%.",
                ]

        status = "AT RISK - below 75%" if overall < 75 else "Safe - above 75%"
        lines.append(f"\nStatus: {status}")
        return "\n".join(lines)

    # ─── TOOL 2: Pending Assignments (deadline not passed + history warning) ───
    @tool
    def check_pending_assignments(dummy: str = "") -> str:
        """
        Get all assignments that are PENDING (not yet submitted) AND whose deadline
        has NOT yet passed. Also warns about past missed submissions.
        Input: any string (ignored).
        Use for: 'What assignments do I have due?', 'What is pending?',
        'Any upcoming deadlines?', 'What should I submit?'
        """
        now = datetime.now(timezone.utc)

        all_assignments = Assignment.objects.filter(
            branch=student.branch
        ).order_by('due_datetime')

        submitted_ids = set(
            AssignmentSubmission.objects.filter(
                student=student, assignment__in=all_assignments
            ).values_list('assignment_id', flat=True)
        )

        # Past missed (deadline passed, not submitted)
        missed_past = [
            a for a in all_assignments
            if a.id not in submitted_ids
            and a.due_datetime is not None
            and a.due_datetime < now
        ]

        # Upcoming pending (deadline not yet passed, not submitted)
        upcoming = [
            a for a in all_assignments
            if a.id not in submitted_ids
            and (a.due_datetime is None or a.due_datetime >= now)
        ]

        lines = [f"Pending Assignments for {student_name}"]

        if not upcoming:
            lines.append("You have no pending assignments due. Great work!")
        else:
            lines.append(f"You have {len(upcoming)} pending assignment(s):\n")
            for a in upcoming:
                if a.due_datetime:
                    remaining = a.due_datetime - now
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    if days > 0:
                        time_str = f"{days}d {hours}h remaining"
                    else:
                        time_str = f"DUE IN {hours}h - SUBMIT SOON!"
                    due_str = a.due_datetime.strftime('%d %b %Y %H:%M')
                else:
                    due_str = "No deadline set"
                    time_str = ""

                lines.append(
                    f"  * {a.title}\n"
                    f"    Course: {a.course.code} - {a.course.name}\n"
                    f"    Due: {due_str} ({time_str})\n"
                    f"    Mode: {a.submission_mode.title()} submission"
                )

        # Show missed history as a warning
        if missed_past:
            lines += [
                "",
                f"IMPORTANT: You have missed {len(missed_past)} past assignment(s):",
            ]
            for mp in missed_past[-3:]:
                due_str = mp.due_datetime.strftime('%d %b %Y') if mp.due_datetime else 'unknown'
                lines.append(f"  x '{mp.title}' (was due {due_str})")
            if len(missed_past) > 3:
                lines.append(f"  ... and {len(missed_past)-3} more missed.")
            lines.append(
                "Please do not miss the upcoming ones — submit before the deadline!"
            )

        return "\n".join(lines)

    # ─── TOOL 3: Fee Status Check ──────────────────────────────────────────────
    @tool
    def check_my_fee_status(dummy: str = "") -> str:
        """
        Get a summary of your fee status: paid, pending, or overdue amounts.
        Shows details for each semester and the total outstanding balance.
        Input: any string (ignored).
        Use for: 'What are my fees?', 'Do I have any pending dues?',
        'Show my fee status', 'How much do I need to pay?'
        """
        fee_records = FeeRecord.objects.filter(student=student).order_by('semester')
        
        if not fee_records.exists():
            return "No fee records found for your account. Please contact the administration."

        lines = [f"Fee Status Summary for {student_name}"]
        total_outstanding = 0
        
        for record in fee_records:
            remaining = record.amount_due - record.amount_paid
            total_outstanding += remaining
            lines.append(
                f"  {record.semester}: {record.status}\n"
                f"    Due: ₹{record.amount_due} | Paid: ₹{record.amount_paid} | Pending: ₹{remaining}"
            )

        lines.append(f"\nTotal Outstanding Balance: ₹{total_outstanding}")
        
        if total_outstanding > 0:
            lines.append("\nPlease ensure your dues are cleared at the earliest to avoid late fees.")
        else:
            lines.append("All your dues are cleared. Great!")

        return "\n".join(lines)

    # ─── TOOL 4: Overall Academic Summary ─────────────────────────────────────
    @tool
    def get_my_academic_summary(dummy: str = "") -> str:
        """
        Get a combined academic overview covering attendance AND assignment status.
        Use for: 'How am I doing?', 'Give me a summary', 'What is my overall status?'
        Input: any string (ignored).
        """
        now = datetime.now(timezone.utc)

        # Attendance
        try:
            att_data = calculate_detailed_attendance(student)
            overall_att = att_data['global_overall_pct']
            att_status = "Safe (above 75%)" if overall_att >= 75 else "AT RISK (below 75%)"
        except Exception:
            overall_att = None
            att_status = "Data unavailable"

        # Assignments
        all_assignments = Assignment.objects.filter(branch=student.branch)
        total_assignments = all_assignments.count()
        submitted_ids = set(
            AssignmentSubmission.objects.filter(
                student=student, assignment__in=all_assignments
            ).values_list('assignment_id', flat=True)
        )
        submitted_count = len(submitted_ids)
        upcoming_pending = sum(
            1 for a in all_assignments
            if a.id not in submitted_ids
            and (a.due_datetime is None or a.due_datetime >= now)
        )

        lines = [
            f"Academic Summary for {student_name}",
            f"Branch: {student.branch} | Semester: {student.current_semester}",
            "",
            f"Attendance: {f'{overall_att:.1f}%' if overall_att is not None else 'N/A'} - {att_status}",
            f"Assignments: {submitted_count}/{total_assignments} submitted, "
            f"{upcoming_pending} pending (not yet due)",
        ]

        if overall_att is not None and overall_att < 75:
            lines.append(
                "\nYour attendance is below 75%! Attend more classes to avoid academic penalties."
            )
        if upcoming_pending > 0:
            lines.append(
                f"\nYou have {upcoming_pending} assignment(s) coming up. "
                f"Ask me 'What assignments do I have due?' for full details."
            )

        # Fees
        fee_records = FeeRecord.objects.filter(student=student)
        total_outstanding = sum((r.amount_due - r.amount_paid) for r in fee_records)
        if total_outstanding > 0:
            lines.append(f"\nYou have a pending fee balance of ₹{total_outstanding}.")

        return "\n".join(lines)

    # ─── Build and return the agent ───────────────────────────────────────────
    tools = [
        check_my_attendance, 
        check_pending_assignments, 
        check_my_fee_status,
        get_my_academic_summary
    ]

    system_prompt = (
        f"You are Academiq, a personal academic assistant for {student_name}. "
        f"Help the student stay on top of their academics and fees.\n\n"
        f"Tool guide:\n"
        f"- Attendance / which subject is low? -> check_my_attendance\n"
        f"- What assignments are due / pending? -> check_pending_assignments\n"
        f"- Fee status / dues / payments -> check_my_fee_status\n"
        f"- General 'how am I doing?' -> get_my_academic_summary\n\n"
        f"Always call the appropriate tool — never guess or fabricate data. "
        f"Be supportive and specific. Highlight what needs immediate attention."
    )

    return create_react_agent(llm, tools, prompt=system_prompt)
