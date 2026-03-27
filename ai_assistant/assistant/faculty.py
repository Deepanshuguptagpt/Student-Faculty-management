import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.tools import tool
from django.conf import settings
from backend.faculty.models import FacultyProfile, Assignment, AssignmentSubmission
from backend.student.models import StudentProfile, Attendance
from ai_assistant.utils import key_rotator

def get_faculty_agent(faculty_id):
    api_key = key_rotator.get_current_key()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0)
    
    @tool
    def analyze_class_performance(branch_name: str):
        """Get insights into class performance and assignments for a branch. Input: Branch name (e.g. 'CSE-1')."""
        try:
            students = StudentProfile.objects.filter(branch=branch_name)
            total_students = students.count()
            if total_students == 0:
                return f"No students found in branch {branch_name}."
            last_assignment = Assignment.objects.filter(branch=branch_name).order_by('-created_at').first()
            if not last_assignment:
                return f"No assignments have been given to {branch_name} yet."
            submissions = AssignmentSubmission.objects.filter(assignment=last_assignment).count()
            return f"Branch: {branch_name}, Last Assignment: '{last_assignment.title}', Submissions: {submissions}/{total_students}."
        except Exception as e:
            return f"Error: {str(e)}"

    @tool
    def search_student_details(enrollment_number: str):
        """Get detailed info (attendance, branch) for a specific student using their enrollment number."""
        try:
            student = StudentProfile.objects.get(enrollment_number=enrollment_number)
            attendance = Attendance.objects.filter(student=student)
            total = attendance.count()
            present = attendance.filter(status='Present').count()
            percentage = (present / total * 100) if total > 0 else 0
            return f"Student: {student.user.name}, Enrollment: {student.enrollment_number}, Branch: {student.branch}, Attendance: {percentage:.2f}%."
        except Exception as e:
            return f"Error: Student with enrollment {enrollment_number} not found."

    tools = [analyze_class_performance, search_student_details]

    faculty = FacultyProfile.objects.get(id=faculty_id)
    system_prompt = f"You are the Academiq Faculty Assistant for Professor {faculty.user.name}. Use the tools provided to look up class-wide performance or specific student details. If the faculty asks about a class, use 'analyze_class_performance'. If they ask about a student, use 'search_student_details'."

    return create_agent(llm, tools, system_prompt=system_prompt)
