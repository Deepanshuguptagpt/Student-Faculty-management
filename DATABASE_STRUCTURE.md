# Database Structure & Management

## Overview
This document describes the database architecture for Academiq. The system uses Django ORM with SQLite as the database backend.

---

## Database Schema

### 1. Authentication Module

#### User Model
**Table:** `authentication_user`

Core user model for all system users (students, faculty, and administrators).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| name | CharField(100) | Required | Full name of the user |
| email | EmailField | Unique, Required | Email address (used for login) |
| role | CharField(10) | Required, Choices | User role: 'student', 'faculty', or 'admin' |
| password | CharField(100) | Default: "ADMIN" | User password |

**Relationships:**
- One-to-One with StudentProfile (if role='student')
- One-to-One with FacultyProfile (if role='faculty')

---

### 2. Student Module

#### StudentProfile Model
**Table:** `backend_student_studentprofile`

Extended profile information for students.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| user_id | ForeignKey | OneToOne → User, CASCADE | Reference to User model |
| enrollment_number | CharField(50) | Unique, Required | Student enrollment number (e.g., 0818CS231001) |
| batch_year | Integer | Required | Year of admission (e.g., 2023) |
| branch | CharField(100) | Required, Choices | Academic branch/specialization |
| course_name | CharField(50) | Default: 'B.tech' | Course program |
| contact_number | CharField(20) | Optional | Phone number |
| address | TextField | Optional | Residential address |
| date_of_birth | DateField | Optional | Date of birth |
| section | CharField(50) | Optional | Class section (e.g., CSE-1, AIML-1) |

**Branch Choices:**
- Computer science engineering
- Artificial Intelligence and machine Learning
- electronics and communication
- Data science
- Information technology
- mechanical engineering
- Civil engineering
- Robotics and Artificial Intelligence
- Internet of things

**Computed Properties:**
- `current_semester`: Calculated based on batch_year and current date
- `current_year`: Derived from current_semester (1st Year, 2nd Year, etc.)

**Enrollment Number Format:**
```
0818CS231001
├─ 0818: Institute code
├─ CS: Branch code
├─ 23: Batch year (2023)
└─ 1001: Student serial number
```

---

#### Course Model
**Table:** `backend_student_course`

Academic courses offered by the institution.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| name | CharField(200) | Required | Full course name |
| code | CharField(50) | Unique, Required | Course code (e.g., CS101) |
| description | TextField | Optional | Course description |
| credits | Integer | Default: 3 | Credit hours |

---

#### Enrollment Model
**Table:** `backend_student_enrollment`

Links students to courses they are enrolled in.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| student_id | ForeignKey | → StudentProfile, CASCADE | Reference to student |
| course_id | ForeignKey | → Course, CASCADE | Reference to course |
| semester | CharField(50) | Required, Choices | Semester of enrollment |
| date_enrolled | DateField | Auto-generated | Enrollment date |

---

#### Attendance Model
**Table:** `backend_student_attendance`

Daily attendance records for students.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| student_id | ForeignKey | → StudentProfile, CASCADE | Reference to student |
| course_id | ForeignKey | → Course, CASCADE | Reference to course |
| date | DateField | Required | Attendance date |
| lecture_number | Integer | Choices: 1-7 | Lecture period number |
| status | CharField(10) | Choices, Default: 'Present' | Attendance status |

**Status Choices:**
- Present
- Absent
- Late

**Unique Constraint:** (student, course, date, lecture_number)

**Business Rules:**
- Faculty can only mark attendance for current or past dates
- Sundays are excluded from attendance marking
- Each student can have one attendance record per lecture per day

---

#### FeeRecord Model
**Table:** `backend_student_feerecord`

Financial records for student fees.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| student_id | ForeignKey | → StudentProfile, CASCADE | Reference to student |
| semester | CharField(50) | Required, Choices | Fee semester |
| amount_due | Decimal(10,2) | Required | Total amount due (₹) |
| amount_paid | Decimal(10,2) | Default: 0.00 | Amount paid (₹) |
| due_date | DateField | Required | Payment deadline |
| status | CharField(20) | Choices, Default: 'Pending' | Payment status |

**Status Choices:**
- Paid
- Pending
- Overdue

---

#### AcademicRecord Model
**Table:** `backend_student_academicrecord`

Student grades and academic performance.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| student_id | ForeignKey | → StudentProfile, CASCADE | Reference to student |
| course_id | ForeignKey | → Course, CASCADE | Reference to course |
| semester | CharField(50) | Required, Choices | Academic semester |
| grade | CharField(5) | Required | Letter grade (A, B, C, etc.) |
| marks | Decimal(5,2) | Optional | Numerical marks |

---

### 3. Faculty Module

#### Department Model
**Table:** `backend_faculty_department`

Academic departments in the institution.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| name | CharField(150) | Unique, Required | Department name |
| code | CharField(20) | Unique, Required | Department code |
| description | TextField | Optional | Department description |

---

#### FacultyProfile Model
**Table:** `backend_faculty_facultyprofile`

Extended profile information for faculty members.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| user_id | ForeignKey | OneToOne → User, CASCADE | Reference to User model |
| department_id | ForeignKey | → Department, SET_NULL | Reference to department |
| designation | CharField(100) | Default: "Assistant Professor" | Job title |
| contact_number | CharField(20) | Optional | Phone number |
| address | TextField | Optional | Residential address |
| date_joined | DateField | Auto-generated | Joining date |

**Validation:**
- Associated user must have role='faculty'

---

#### FacultyCourseAssignment Model
**Table:** `backend_faculty_facultycourseassignment`

Maps faculty members to courses they teach.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| faculty_id | ForeignKey | → FacultyProfile, CASCADE | Reference to faculty |
| course_id | ForeignKey | → Course, CASCADE | Reference to course |
| semester | CharField(50) | Required, Choices | Teaching semester |

**Unique Constraint:** (faculty, course, semester)

---

#### Assignment Model
**Table:** `backend_faculty_assignment`

Assignments created by faculty for students.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique identifier |
| title | CharField(250) | Required | Assignment title |
| description | TextField | Optional | Assignment details |
| faculty_id | ForeignKey | → FacultyProfile, CASCADE | Creator faculty |
| course_id | ForeignKey | → Course, CASCADE | Related course |
| branch | CharField(100) | Required, Choices | Target branch |
| year | CharField(20) | Optional | Target year (1st, 2nd, etc.) |
| created_at | DateTimeField | Auto-generated | Creation timestamp |
| due_date | DateField | Optional | Submission deadline |

---

## Database Relationships

### Entity Relationship Diagram (Textual)

```
User (1) ←→ (1) StudentProfile
User (1) ←→ (1) FacultyProfile

StudentProfile (1) ←→ (N) Enrollment
StudentProfile (1) ←→ (N) Attendance
StudentProfile (1) ←→ (N) FeeRecord
StudentProfile (1) ←→ (N) AcademicRecord

Course (1) ←→ (N) Enrollment
Course (1) ←→ (N) Attendance
Course (1) ←→ (N) AcademicRecord
Course (1) ←→ (N) FacultyCourseAssignment
Course (1) ←→ (N) Assignment

FacultyProfile (1) ←→ (N) FacultyCourseAssignment
FacultyProfile (1) ←→ (N) Assignment
FacultyProfile (N) ←→ (1) Department
```

---

## Data Management

### Database File
- **Location:** `db.sqlite3` (root directory)
- **Backup:** `db_backup.sqlite3`
- **Type:** SQLite3

### Migrations
All database schema changes are managed through Django migrations located in:
- `authentication/migrations/`
- `backend/student/migrations/`
- `backend/faculty/migrations/`
- `backend/administration/migrations/`

### Common Operations

#### Apply Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

#### Create Backup
```bash
cp db.sqlite3 db_backup.sqlite3
```

#### Access Database Shell
```bash
python manage.py dbshell
```

#### Django Shell (ORM)
```bash
python manage.py shell
```

---

## Data Import Scripts

The system includes several scripts for bulk data import from Excel files:

| Script | Purpose | Source File |
|--------|---------|-------------|
| `import_students.py` | Import CSE students | `CSE1.xlsx` |
| `import_cs2.py` | Import CS2 students | `CS2_with_emails.xlsx` |
| `import_cs3.py` | Import CS3 students | `CS3_with_emails.xlsx` |
| `import_aiml_students.py` | Import AIML students | `aiml_with_correct_emails.xlsx` |
| `import_ds_students.py` | Import Data Science students | `Ds-Student-List.xlsx` |
| `import_it.py` | Import IT students | `IT_list_with_emails.xlsx` |
| `import_staff.py` | Import faculty members | `Facultylist.xlsx` |

### Import Script Pattern
```python
import os
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User
from backend.student.models import StudentProfile

# Read Excel file
df = pd.read_excel('filename.xlsx')

# Process each row
for index, row in df.iterrows():
    # Extract batch year from enrollment number
    enrollment = str(row['Enrollment No'])
    year_str = enrollment[6:8]  # Position 6-8 contains year
    batch_year = int("20" + year_str)
    
    # Create or update user and profile
    user, created = User.objects.get_or_create(
        email=row['Email'],
        defaults={'name': row['Name'], 'role': 'student', 'password': 'ADMIN'}
    )
    
    profile, created = StudentProfile.objects.update_or_create(
        user=user,
        defaults={
            'enrollment_number': enrollment,
            'batch_year': batch_year,
            'branch': 'Branch Name',
            'course_name': 'B.tech',
            'section': 'Section Name'
        }
    )
```

---

## Data Integrity Rules

### Cascade Deletion
- Deleting a User automatically deletes associated StudentProfile or FacultyProfile
- Deleting a StudentProfile removes all related Enrollment, Attendance, FeeRecord, and AcademicRecord entries
- Deleting a Course removes all related enrollments and assignments

### Unique Constraints
- User email must be unique across the system
- Student enrollment numbers must be unique
- Course codes must be unique
- Department codes must be unique
- Attendance records are unique per (student, course, date, lecture_number)
- Faculty course assignments are unique per (faculty, course, semester)

### Validation Rules
- FacultyProfile user must have role='faculty'
- Attendance dates cannot be in the future
- Attendance cannot be marked on Sundays
- Batch year extraction from enrollment number format: `0818[BRANCH][YY][SERIAL]`

---

## Performance Considerations

### Indexes
Django automatically creates indexes on:
- Primary keys (id fields)
- Foreign keys
- Unique fields (email, enrollment_number, course code)

### Query Optimization
Use `select_related()` for OneToOne and ForeignKey relationships:
```python
students = StudentProfile.objects.select_related('user').all()
faculty = FacultyProfile.objects.select_related('user', 'department').all()
```

Use `prefetch_related()` for reverse ForeignKey and ManyToMany:
```python
students = StudentProfile.objects.prefetch_related('enrollments', 'attendance_records').all()
```

---

## Backup & Recovery

### Manual Backup
```bash
# Backup database
cp db.sqlite3 backups/db_$(date +%Y%m%d_%H%M%S).sqlite3

# Restore from backup
cp backups/db_20260313_120000.sqlite3 db.sqlite3
```

### Export Data
```bash
# Export all data to JSON
python manage.py dumpdata > backup.json

# Export specific app
python manage.py dumpdata backend.student > student_data.json

# Import data
python manage.py loaddata backup.json
```

---

## Security Notes

1. **Default Password:** All imported users have password='ADMIN' - should be changed on first login
2. **Email Uniqueness:** Email serves as the unique identifier for authentication
3. **Role-Based Access:** User roles ('student', 'faculty', 'admin') control dashboard access
4. **Data Privacy:** Student and faculty personal information should be handled per privacy regulations

---

## Future Enhancements

Potential database improvements:
- Add password hashing (currently using plain text)
- Implement soft delete (archive instead of delete)
- Add audit logs for data changes
- Create indexes for frequently queried fields
- Add database connection pooling for production
- Migrate to PostgreSQL for better performance at scale
