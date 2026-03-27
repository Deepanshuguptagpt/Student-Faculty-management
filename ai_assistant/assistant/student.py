import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.tools import tool
from django.conf import settings
from backend.faculty.models import Assignment, AssignmentSubmission
from backend.student.models import StudentProfile, Attendance
from backend.student.utils import calculate_detailed_attendance
from ai_assistant.utils import key_rotator

def get_student_assignments(student_id):
    try:
        student = StudentProfile.objects.get(id=student_id)
        assignments = Assignment.objects.filter(branch=student.branch)
        result = []
        for ass in assignments:
            submission = AssignmentSubmission.objects.filter(assignment=ass, student=student).first()
            status = "Submitted" if submission else "Pending"
            result.append(f"- {ass.title} (Due: {ass.due_datetime}, Status: {status})")
        return "\n".join(result) if result else "You have no assignments at the moment."
    except Exception as e:
        return f"Database error: {str(e)}"

def get_student_attendance(student_id):
    try:
        student = StudentProfile.objects.get(id=student_id)
        # Use the official utility for consistency
        data = calculate_detailed_attendance(student)
        percentage = data['global_overall_pct']
        total = data.get('total_overall', sum(d['total_all'] for d in data['course_data']))
        present = data.get('present_overall', sum(d['present_all'] for d in data['course_data']))
        
        return f"Your overall attendance is {percentage}% ({present}/{total} lectures present). This matches your official dashboard."
    except Exception as e:
        return f"Error fetching attendance: {str(e)}"

def get_student_agent(student_id):
    api_key = key_rotator.get_current_key()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)

    @tool
    def check_my_assignments(dummy_input: str):
        """Get the current student's pending and submitted assignments. Takes any string as input."""
        return get_student_assignments(student_id)

    @tool
    def check_my_attendance(dummy_input: str):
        """Get the current student's attendance summary. Takes any string as input."""
        return get_student_attendance(student_id)

    tools = [check_my_assignments, check_my_attendance]

    student = StudentProfile.objects.get(id=student_id)
    system_prompt = f"You are an assistant for student {student.user.name}. Use the tools provided to fetch their data. If they ask for assignments, call check_my_assignments. If they ask for attendance, call check_my_attendance. Always provide a clear summary of the tool results. Your attendance data comes directly from the official records used in the dashboard."

    return create_agent(llm, tools, system_prompt=system_prompt)
