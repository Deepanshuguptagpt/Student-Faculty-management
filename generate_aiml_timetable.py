import os
import django
from datetime import date, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile, Course, Enrollment, Attendance
from backend.faculty.models import FacultyProfile, FacultyCourseAssignment, Department

# --- CONFIGURATION ---
BRANCH_NAME = 'Artificial Intelligence and machine Learning'
SEMESTER = '6th Semester'
START_DATE = date(2026, 2, 11)
END_DATE = date(2026, 3, 13)
BATCH_DIVIDER = '0818CL231040'

# Definition of courses and their intended faculty
# tuples: (Title, Code, FacultyName)
MAIN_COURSES = [
    ("Theory of Computation", "AL-601", "Atish Mishra"),
    ("Computer Networks", "AL-602", "Smita Marwadi"),
    ("Image and Video Processing", "AL-603A", "Ratnesh Chaturvedi"),
    ("Cloud Computing", "AL-604A", "Nishant Vijayvargiya"),
]

MAIN_LABS = [
    ("Theory of Computation Lab", "AL-601[P]", "Atish Mishra"),
    ("Computer Networks Lab", "AL-602[P]", "Smita Marwadi"),
    ("Image and Video Processing Lab", "AL-603A[P]", "Ratnesh Chaturvedi"),
    ("Cloud Computing Lab", "AL-604A[P]", "Nishant Vijayvargiya"),
]

# (Title, FacultyName) - code is derived from title for DB constraints, but we leave blank if possible or generate a simple one. DB demands unique 'code'. We'll use title as code.
EXTRA_COURSES = [
    ("Aptitude", "Abhishek Bhatnagar"),
    ("PDP", "Jaya Singh"),
    ("Minor Lab", "Sukrati Agrawal"),
    ("Competitive Programming", "Shivani Katare"),
]

# Timetable structure: Day of week (0=Mon, 4=Fri) -> {lecture_number: [(CourseType, CourseIdentifier)]}
# Course identifiers link back to the structures above:
# strings match exactly the titles above.
# For labs with A/B batches, we store tuples like (Batch, Title)
TIMETABLE = {
    0: { # Monday
        1: ("Main", "Image and Video Processing"),
        2: ("Main", "Cloud Computing"),
        3: ("Extra", "PDP"),
        4: ("Main", "Computer Networks"),
        5: ("Extra", "Minor Lab"),
        6: ("Extra", "Minor Lab"),
        7: ("Main", "Theory of Computation")
    },
    1: { # Tuesday
        1: ("Main", "Image and Video Processing"),
        2: ("Main", "Cloud Computing"),
        3: ("Main", "Theory of Computation"),
        4: ("Extra", "PDP"),
        5: ("Main", "Computer Networks"),
        6: ("Extra", "Competitive Programming"),
        7: ("Extra", "Competitive Programming")
    },
    2: { # Wednesday
        1: ("Extra", "Aptitude"),
        2: ("Extra", "Aptitude"),
        3: ("Main", "Computer Networks"),
        4: ("Main", "Theory of Computation"),
        5: ("Split", {"B1": "Computer Networks Lab", "B2": "Theory of Computation Lab"}),
        6: ("Split", {"B1": "Computer Networks Lab", "B2": "Theory of Computation Lab"}),
        7: ("Main", "Image and Video Processing")
    },
    3: { # Thursday
        1: ("Split", {"B1": "Image and Video Processing Lab", "B2": "Cloud Computing Lab"}),
        2: ("Split", {"B1": "Image and Video Processing Lab", "B2": "Cloud Computing Lab"}),
        3: ("Split", {"B2": "Computer Networks Lab", "B1": "Theory of Computation Lab"}),
        4: ("Split", {"B2": "Computer Networks Lab", "B1": "Theory of Computation Lab"}),
        5: ("Main", "Cloud Computing"),
        6: ("Extra", "PDP"),
        7: ("Main", "Theory of Computation")
    },
    4: { # Friday
        1: ("Split", {"B2": "Image and Video Processing Lab", "B1": "Cloud Computing Lab"}),
        2: ("Split", {"B2": "Image and Video Processing Lab", "B1": "Cloud Computing Lab"}),
        3: ("Main", "Computer Networks"),
        4: ("Main", "Image and Video Processing"),
        5: ("Extra", "Competitive Programming Lab"), # Assuming from context this goes to Shivani Katare (Competitive Programming)
        6: ("Extra", "Competitive Programming Lab"), # We will map this to the 'Competitive Programming' course
        7: ("Skip", None) # Sport/Library
    }
}

def main():
    print("--- 1. Clearing Existing Assignments ---")
    FacultyCourseAssignment.objects.all().delete()
    print("Deleted all existing FacultyCourseAssignments.")

    aiml_students = StudentProfile.objects.filter(branch__iexact=BRANCH_NAME)
    student_ids = aiml_students.values_list('id', flat=True)
    Enrollment.objects.filter(student_id__in=student_ids).delete()
    print(f"Deleted old course enrollments for {len(student_ids)} AIML students.")

    # Drop existing attendances for this timeframe for these students to ensure clean state
    Attendance.objects.filter(student_id__in=student_ids, date__gte=START_DATE, date__lte=END_DATE).delete()
    print("Cleaned up old attendance records for the target period.")

    print("\n--- 2. Setting Up Faculty & Courses ---")
    # Helper to get/create faculty
    def get_faculty(name):
        email = f"{name.replace(' ', '.').lower()}@college.edu"
        user, _ = User.objects.get_or_create(email=email, defaults={'name': name, 'role': 'faculty', 'password': 'ADMIN'})
        if user.role != 'faculty':
            user.role = 'faculty'
            user.save()
        dept, _ = Department.objects.get_or_create(code='CSE', defaults={'name': 'Computer Science Engineering'})
        fac_prof, _ = FacultyProfile.objects.get_or_create(user=user, defaults={'department': dept})
        return fac_prof

    course_map = {} # title -> Course logic object

    # Create Main Courses
    for title, code, fac_name in MAIN_COURSES:
        course, _ = Course.objects.get_or_create(code=code, defaults={'name': title})
        fac = get_faculty(fac_name)
        FacultyCourseAssignment.objects.get_or_create(faculty=fac, course=course, semester=SEMESTER)
        course_map[title] = course

    # Create Lab Courses
    for title, code, fac_name in MAIN_LABS:
        course, _ = Course.objects.get_or_create(code=code, defaults={'name': title})
        fac = get_faculty(fac_name)
        FacultyCourseAssignment.objects.get_or_create(faculty=fac, course=course, semester=SEMESTER)
        course_map[title] = course

    # Create Extra Courses
    for title, fac_name in EXTRA_COURSES:
        code = title.upper()[:15].replace(" ", "_") # e.g. APTITUDE, PDP, MINOR_LAB
        course, _ = Course.objects.get_or_create(code=code, defaults={'name': title})
        fac = get_faculty(fac_name)
        FacultyCourseAssignment.objects.get_or_create(faculty=fac, course=course, semester=SEMESTER)
        course_map[title] = course
        # Map "Competitive Programming Lab" to the same extra course
        if title == "Competitive Programming":
            course_map["Competitive Programming Lab"] = course


    print("\n--- 3. Enrolling Students ---")
    enrollments_to_create = []
    # Identify b1 and b2 based on enrollment string comparison
    students_b1 = []
    students_b2 = []
    
    for s in aiml_students:
        if s.enrollment_number <= BATCH_DIVIDER:
            students_b1.append(s)
        else:
            students_b2.append(s)

        # Enroll all students in all these newly created courses for 6th sem
        for c in course_map.values():
            enrollments_to_create.append(Enrollment(student=s, course=c, semester=SEMESTER))
            
    Enrollment.objects.bulk_create(enrollments_to_create, ignore_conflicts=True)
    print(f"Assigned {len(course_map)} courses to {len(students_b1)} B1 students and {len(students_b2)} B2 students.")

    print("\n--- 4. Generating Attendance ---")
    current_date = START_DATE
    attendance_records = []

    days_processed = 0
    while current_date <= END_DATE:
        day_of_week = current_date.weekday()
        
        # Skip weekennds
        if day_of_week >= 5:
            current_date += timedelta(days=1)
            continue
            
        daily_schedule = TIMETABLE.get(day_of_week, {})
        
        for lect_num, instruction in daily_schedule.items():
            l_type = instruction[0]
            l_val = instruction[1]
            
            if l_type == "Skip":
                continue
                
            if l_type in ["Main", "Extra"]:
                course = course_map[l_val]
                # Present 90% of time, Absent 10%
                for s in aiml_students:
                    status = random.choices(['Present', 'Absent'], weights=[90, 10])[0]
                    attendance_records.append(Attendance(
                        student=s, course=course, date=current_date, lecture_number=lect_num, status=status
                    ))
                    
            elif l_type == "Split":
                course_b1_title = l_val.get("B1")
                course_b2_title = l_val.get("B2")
                
                if course_b1_title:
                    course_b1 = course_map[course_b1_title]
                    for s in students_b1:
                        status = random.choices(['Present', 'Absent'], weights=[90, 10])[0]
                        attendance_records.append(Attendance(
                            student=s, course=course_b1, date=current_date, lecture_number=lect_num, status=status
                        ))
                
                if course_b2_title:
                    course_b2 = course_map[course_b2_title]
                    for s in students_b2:
                        status = random.choices(['Present', 'Absent'], weights=[90, 10])[0]
                        attendance_records.append(Attendance(
                            student=s, course=course_b2, date=current_date, lecture_number=lect_num, status=status
                        ))
        
        current_date += timedelta(days=1)
        days_processed += 1
        
    # Chunk creation to avoid SQlite limits
    from itertools import islice
    def batched(iterable, n):
        it = iter(iterable)
        while batch := list(islice(it, n)):
            yield batch
            
    total_created = 0
    for batch in batched(attendance_records, 5000):
        Attendance.objects.bulk_create(batch, ignore_conflicts=True)
        total_created += len(batch)
        
    print(f"Generated {total_created} attendance records across {days_processed} working days.")
    print("Operation Complete.")

if __name__ == '__main__':
    main()
