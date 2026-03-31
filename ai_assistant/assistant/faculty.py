"""
Faculty AI Assistant — Agentic, context-aware.

All tools are scoped to ONLY the courses the faculty member is assigned to teach.
Uses LangGraph's create_react_agent (LangChain 1.x compatible).
"""

from datetime import datetime, timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from backend.faculty.models import FacultyProfile, FacultyCourseAssignment, Assignment, AssignmentSubmission
from backend.student.models import StudentProfile, Attendance, Enrollment
from ai_assistant.utils import key_rotator


def get_faculty_agent(faculty_id):
    api_key = key_rotator.get_current_key()
    llm_kwargs = {"model": "gemini-2.5-flash", "temperature": 0}
    if api_key:  # only pass explicitly if we have a key; otherwise let the library read GOOGLE_API_KEY env var
        llm_kwargs["google_api_key"] = api_key
    llm = ChatGoogleGenerativeAI(**llm_kwargs)

    # ─── Resolve faculty and their assigned courses once ──────────────────────
    faculty = FacultyProfile.objects.select_related('user', 'department').get(id=faculty_id)
    faculty_name = faculty.user.name

    assigned_course_ids = list(
        FacultyCourseAssignment.objects.filter(faculty=faculty)
        .values_list('course_id', flat=True)
    )

    # ─── TOOL 1: Low-attendance students (scoped to faculty's courses) ─────────
    @tool
    def get_low_attendance_students(threshold: str = "75") -> str:
        """
        Find students with low attendance ONLY in the courses this faculty teaches.
        Input: attendance threshold percentage as a string (default "75").
        Returns a list of students, per course, who are below the threshold.
        Use this when the faculty asks: 'Which students have low attendance?',
        'Who is below 75%?', 'Show attendance risk students'.
        """
        try:
            cutoff = float(threshold)
        except ValueError:
            cutoff = 75.0

        if not assigned_course_ids:
            return f"You ({faculty_name}) are not assigned to teach any courses yet."

        course_assignments = FacultyCourseAssignment.objects.filter(
            faculty=faculty
        ).select_related('course')

        results = []
        for ca in course_assignments:
            course = ca.course
            enrollments = Enrollment.objects.filter(course=course).select_related('student__user')
            at_risk = []
            for enr in enrollments:
                student = enr.student
                att_qs = Attendance.objects.filter(student=student, course=course)
                total = att_qs.count()
                present = att_qs.filter(status='Present').count()
                pct = (present / total * 100) if total > 0 else 0.0
                if pct < cutoff:
                    at_risk.append(
                        f"  - {student.user.name} ({student.enrollment_number}): {pct:.1f}% ({present}/{total})"
                    )

            if at_risk:
                results.append(
                    f"\nCourse: {course.code} - {course.name}\n" + "\n".join(at_risk)
                )

        if not results:
            return (
                f"No students in your courses are below {cutoff:.0f}% attendance. "
                f"Courses checked: {', '.join(ca.course.code for ca in course_assignments)}"
            )

        return (
            f"Students below {cutoff:.0f}% attendance in YOUR courses ({faculty_name}):\n"
            + "".join(results)
        )

    # ─── TOOL 2: Struggling students — full academic summary ──────────────────
    @tool
    def get_struggling_students(attendance_threshold: str = "75") -> str:
        """
        Identify students who are falling behind academically — covers attendance
        AND assignment submissions — only for the courses this faculty teaches.
        Input: attendance threshold as a string (default "75").
        Use for: 'Who is falling behind?', 'Show at-risk students', 'Which students need help?'.
        """
        try:
            cutoff = float(attendance_threshold)
        except ValueError:
            cutoff = 75.0

        if not assigned_course_ids:
            return f"You ({faculty_name}) are not assigned to any courses yet."

        student_ids = set(
            Enrollment.objects.filter(course_id__in=assigned_course_ids)
            .values_list('student_id', flat=True)
        )

        if not student_ids:
            return "No students are currently enrolled in your courses."

        struggling = []
        for student in StudentProfile.objects.filter(id__in=student_ids).select_related('user'):
            # Attendance across faculty's courses only
            total_present = 0
            total_lectures = 0
            course_lines = []
            for cid in assigned_course_ids:
                att_qs = Attendance.objects.filter(student=student, course_id=cid)
                t = att_qs.count()
                p = att_qs.filter(status='Present').count()
                if t > 0:
                    total_present += p
                    total_lectures += t
                    course_lines.append(f"    - Course {cid}: {p/t*100:.1f}%")

            overall_att = (total_present / total_lectures * 100) if total_lectures > 0 else None

            # Assignments from this faculty only
            faculty_assignments = Assignment.objects.filter(faculty=faculty)
            total_assigned = faculty_assignments.count()
            submitted = AssignmentSubmission.objects.filter(
                student=student, assignment__in=faculty_assignments
            ).count()
            pending = total_assigned - submitted

            att_risk = overall_att is not None and overall_att < cutoff
            assign_risk = (total_assigned > 0) and (pending / total_assigned > 0.4)

            if att_risk or assign_risk:
                issues = []
                if att_risk:
                    issues.append(f"  Attendance: {overall_att:.1f}% (below {cutoff:.0f}%)")
                if assign_risk:
                    issues.append(
                        f"  Assignments: {pending}/{total_assigned} pending "
                        f"({pending/total_assigned*100:.0f}% unsubmitted)"
                    )
                block = f"\n{student.user.name} (#{student.enrollment_number}):\n" + "\n".join(issues)
                struggling.append(block)

        if not struggling:
            return (
                f"No students appear to be struggling "
                f"(threshold: {cutoff:.0f}% attendance, <40% assignments pending)."
            )

        return f"Struggling Students in YOUR courses ({faculty_name}):\n" + "".join(struggling)

    # ─── TOOL 3: Class performance for a specific course ──────────────────────
    @tool
    def get_course_performance(course_code: str) -> str:
        """
        Get a performance summary for a specific course that this faculty teaches.
        Input: The course code (e.g. 'CS-601', 'AL-401').
        Use for: 'How is my CS-601 class doing?', 'Stats for AL-401'.
        """
        ca = FacultyCourseAssignment.objects.filter(
            faculty=faculty, course__code__iexact=course_code.strip()
        ).select_related('course').first()

        if not ca:
            taught_codes = ", ".join(
                FacultyCourseAssignment.objects.filter(faculty=faculty)
                .values_list('course__code', flat=True)
            ) or "none"
            return (
                f"You don't teach a course with code '{course_code}'. "
                f"Your assigned courses: {taught_codes}"
            )

        course = ca.course
        enrollments = Enrollment.objects.filter(course=course).select_related('student__user')
        total_students = enrollments.count()
        if total_students == 0:
            return f"No students enrolled in {course.code} - {course.name}."

        below_75 = 0
        all_pcts = []
        for enr in enrollments:
            att_qs = Attendance.objects.filter(student=enr.student, course=course)
            t = att_qs.count()
            p = att_qs.filter(status='Present').count()
            pct = (p / t * 100) if t > 0 else 0
            all_pcts.append(pct)
            if pct < 75:
                below_75 += 1

        avg_att = sum(all_pcts) / len(all_pcts) if all_pcts else 0

        latest_ass = Assignment.objects.filter(
            faculty=faculty, course=course
        ).order_by('-created_at').first()

        assignment_info = "No assignments given yet."
        if latest_ass:
            subs = AssignmentSubmission.objects.filter(assignment=latest_ass).count()
            due_str = latest_ass.due_datetime.strftime('%d %b %Y %H:%M') if latest_ass.due_datetime else 'No deadline'
            assignment_info = (
                f"Latest: '{latest_ass.title}' | "
                f"Submissions: {subs}/{total_students} | Due: {due_str}"
            )

        return (
            f"Course: {course.code} - {course.name}\n"
            f"Enrolled: {total_students} students\n"
            f"Avg Attendance: {avg_att:.1f}%\n"
            f"Below 75%: {below_75} students\n"
            f"Assignment: {assignment_info}"
        )

    # ─── TOOL 4: Specific student lookup ──────────────────────────────────────
    @tool
    def get_student_profile(enrollment_number: str) -> str:
        """
        Get detailed academic info for a specific student using their enrollment number.
        Input: The student's enrollment number (e.g. '2023001').
        Use for: 'Tell me about student 2023001', 'How is [enrollment] doing?'
        """
        try:
            student = StudentProfile.objects.select_related('user').get(
                enrollment_number=enrollment_number.strip()
            )
        except StudentProfile.DoesNotExist:
            return f"No student found with enrollment number '{enrollment_number}'."

        lines = [
            f"Student: {student.user.name}",
            f"Enrollment: {student.enrollment_number}",
            f"Branch: {student.branch}",
            f"Semester: {student.current_semester}",
            "",
            "Attendance in YOUR courses:",
        ]

        course_assignments = FacultyCourseAssignment.objects.filter(
            faculty=faculty
        ).select_related('course')

        any_att = False
        for ca in course_assignments:
            course = ca.course
            att_qs = Attendance.objects.filter(student=student, course=course)
            t = att_qs.count()
            if t == 0:
                continue
            any_att = True
            p = att_qs.filter(status='Present').count()
            pct = (p / t * 100)
            flag = "[LOW]" if pct < 75 else "[OK]"
            lines.append(f"  {flag} {course.code}: {pct:.1f}% ({p}/{t})")

        if not any_att:
            lines.append("  No attendance records for your courses.")

        faculty_assignments = Assignment.objects.filter(faculty=faculty)
        total = faculty_assignments.count()
        submitted = AssignmentSubmission.objects.filter(
            student=student, assignment__in=faculty_assignments
        ).count()

        lines += [
            "",
            f"Your Assignments: {submitted}/{total} submitted, {total-submitted} pending",
        ]
        return "\n".join(lines)

    # ─── TOOL 5: Attendance List Query ────────────────────────────────────────
    @tool
    def get_attendance_list(date_str: str, lecture_number: str, status: str = "Absent", course_code: str = None) -> str:
        """
        Get a list of students who were either 'Present' or 'Absent' on a specific date and lecture.
        Input: 
            date_str: The date (e.g., '2026-03-25').
            lecture_number: The lecture number (e.g., '3').
            status: Either 'Present' or 'Absent' (default is 'Absent').
            course_code: Optional course code to filter further.
        Use for: 'Who was absent on March 25th in my 3rd lecture?', 'List present students for AL-401'.
        """
        from datetime import datetime
        try:
            # Flexible date parsing — use dateutil if available
            from dateutil import parser
            dt = parser.parse(date_str).date()
        except:
            return f"Invalid date format: '{date_str}'. Please use YYYY-MM-DD or a clear date name."

        status_cap = status.strip().capitalize()
        if status_cap not in ['Present', 'Absent']:
            status_cap = 'Absent' # fallback

        # Base query for attendance
        query = Attendance.objects.filter(
            date=dt,
            lecture_number=int(lecture_number),
            status=status_cap,
            course_id__in=assigned_course_ids
        ).select_related('student__user', 'course')

        if course_code:
            query = query.filter(course__code__iexact=course_code.strip())

        if not query.all().exists():
            return f"No students were marked as '{status_cap}' on {dt} for lecture {lecture_number} in your courses."

        # Group by course for clarity
        results_by_course = {}
        for att in query:
            c_name = f"{att.course.code} - {att.course.name}"
            if c_name not in results_by_course:
                results_by_course[c_name] = []
            results_by_course[c_name].append(f"  - {att.student.user.name} ({att.student.enrollment_number})")

        output_lines = [f"Students marked as '{status_cap}' on {dt} (Lecture {lecture_number}):"]
        for course, students in results_by_course.items():
            output_lines.append(f"\nCourse: {course}")
            output_lines.extend(students)

        return "\n".join(output_lines)

    # ─── Build and return the agent ───────────────────────────────────────────
    tools = [
        get_low_attendance_students,
        get_struggling_students,
        get_course_performance,
        get_student_profile,
        get_attendance_list,
    ]

    taught_codes = ", ".join(
        FacultyCourseAssignment.objects.filter(faculty=faculty)
        .values_list('course__code', flat=True)
    ) or "none assigned yet"

    system_prompt = (
        f"You are Academiq, a smart academic assistant for Professor {faculty_name}, "
        f"who teaches: {taught_codes}. "
        f"You help faculty understand student performance ONLY for their own courses. "
        f"Always use tools to get real data. Never fabricate numbers.\n\n"
        f"Tool guide:\n"
        f"- 'Which students have low attendance?' -> get_low_attendance_students\n"
        f"- 'Who is falling behind / struggling?' -> get_struggling_students\n"
        f"- 'How is course X doing?' -> get_course_performance (pass course code)\n"
        f"- 'Tell me about student [enrollment]' -> get_student_profile\n"
        f"- 'Who was present/absent on [date] in lecture [number]?' -> get_attendance_list\n"
        f"Always be specific, data-driven, and professional."
    )

    return create_react_agent(llm, tools, prompt=system_prompt)
