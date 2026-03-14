import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.faculty.models import FacultyProfile, FacultyCourseAssignment
from backend.student.models import Enrollment, Attendance
from authentication.models import User

# Actual existing faculty emails provided by the system
FACULTY_MAPPING = {
    "Atish Mishra": "ratnesh.chaturvedi@indoreinstitute.com", # As printed by the previous fallback script
    "Smita Marwadi": "smita.marawdi@indoreinstitute.com",
    "Ratnesh Chaturvedi": "ratnesh.chaturvedi@indoreinstitute.com",
    "Nishant Vijayvargiya": "nishant.vijay@indoreinstitute.com",
    "Abhishek Bhatnagar": "abhishek.bhatnagar@indoreinstitute.com",
    "Jaya Singh": "jaya.singh@indoreinstitute.com",
    "Sukrati Agrawal": "sukrati.agrawal@indoreinstitute.com",
    "Shivani Katare": "shivani.katare@indoreinstitute.com"
}
# Note: I noticed Ratnesh Chaturvedi was the fallback User. 
# Let's write a smarter search to find the real existing users by matching names loosely 
# instead of hardcoding, as some emails might have typos in the DB.

def get_real_faculty(name):
    # Try exact match first
    users = User.objects.filter(role='faculty', name__icontains=name.split()[0])
    if users.exists():
        # returns the first match
        user = users.first()
        prof, _ = FacultyProfile.objects.get_or_create(user=user)
        return prof
        
    print(f"Could not find existing profile for {name}. Falling back to default.")
    return FacultyProfile.objects.first()

def fix_assignments():
    print("--- Fixing Faculty Assignments ---")
    assignments = FacultyCourseAssignment.objects.all()
    
    updated_count = 0
    for a in assignments:
        # e.g AL-601
        # Which faculty was this supposed to be?
        # Re-map by looking up the name we originally wanted
        course_name = a.course.name
        
        # Determine intended faculty from global variables from the previous script
        intended_fac_name = None
        
        if "Theory of Computation" in course_name:
            intended_fac_name = "Atish Mishra"
        elif "Computer Networks" in course_name:
            intended_fac_name = "Smita Marwadi"
        elif "Image and Video" in course_name:
            intended_fac_name = "Ratnesh Chaturvedi"
        elif "Cloud Computing" in course_name:
            intended_fac_name = "Nishant Vijayvargiya"
        elif "Aptitude" in course_name:
             intended_fac_name = "Abhishek Bhatnagar"
        elif "PDP" in course_name:
             intended_fac_name = "Jaya Singh"
        elif "Minor Lab" in course_name:
             intended_fac_name = "Sukrati Agrawal"
        elif "Competitive Programming" in course_name:
             intended_fac_name = "Shivani Katare"
             
        if intended_fac_name:
            real_prof = get_real_faculty(intended_fac_name)
            if a.faculty != real_prof:
                print(f"Updating {course_name}: {a.faculty.user.email} -> {real_prof.user.email} ({real_prof.user.name})")
                a.faculty = real_prof
                a.save()
                updated_count += 1
                
    print(f"Fixed {updated_count} assignments to point to correct existing user profiles.")
    
    # Cleanup dummy accounts created in previous script
    dummies = User.objects.filter(email__endswith='@college.edu')
    print(f"Found {dummies.count()} dummy accounts to remove.")
    dummies.delete()

if __name__ == '__main__':
    fix_assignments()
