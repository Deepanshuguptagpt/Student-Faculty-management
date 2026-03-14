import os
import django
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.views import student_attendance
from backend.student.models import StudentProfile

def test_view():
    factory = RequestFactory()
    request = factory.get('/student/attendance/')
    
    # Mock session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    # Use the first student profile for testing
    student = StudentProfile.objects.filter(branch__iexact='Artificial Intelligence and machine Learning').first()
    if not student:
        print("No AIML student found to test.")
        return
        
    request.session['student_email'] = student.user.email
    
    print(f"Testing attendance view for student: {student.user.name} ({student.enrollment_number})")
    
    response = student_attendance(request)
    context = response.context_data if hasattr(response, 'context_data') else getattr(response, 'context', {})
    
    if not context:
        # If it's a TemplateResponse or similar, it might be in different places depending on Django version
        print("Could not extract context directly from response object. Check if it's a standard render() call.")
        return

    print(f"\nGlobal Percentages:")
    print(f" - Theory: {context.get('global_theory_pct')}%")
    print(f" - Practical: {context.get('global_practical_pct')}%")
    print(f" - Overall: {context.get('global_overall_pct')}%")
    
    print(f"\nCourse Groups Found: {len(context.get('course_data', []))}")
    for course in context.get('course_data', []):
        print(f"\nCourse: {course['name']} ({course['base_code']})")
        print(f" - Percentage: {course['percentage']:.1f}%")
        print(f" - Theory: {course['theory']['present']}/{course['theory']['total']}")
        print(f" - Practical: {course['practical']['present']}/{course['practical']['total']}")
        print(f" - Faculty: {course['faculty']}")

if __name__ == '__main__':
    test_view()
