from django.db import models
from authentication.models import User

SEMESTER_CHOICES = [
    ('1st Semester', '1st Semester'),
    ('2nd Semester', '2nd Semester'),
    ('3rd Semester', '3rd Semester'),
    ('4th Semester', '4th Semester'),
    ('5th Semester', '5th Semester'),
    ('6th Semester', '6th Semester'),
    ('7th Semester', '7th Semester'),
    ('8th Semester', '8th Semester'),
]
BRANCH_CHOICES = [
    ('Computer science engineering', 'Computer science engineering'),
    ('Artificial Intelligence and machine Learning', 'Artificial Intelligence and machine Learning'),
    ('electronics and communication', 'electronics and communication'),
    ('Data science', 'Data science'),
    ('Information technology', 'Information technology'),
    ('mechanical engineering', 'mechanical engineering'),
    ('Civil engineering', 'Civil engineering'),
    ('Robotics and Artificial Intelligence', 'Robotics and Artificial Intelligence'),
    ('Internet of things', 'Internet of things')
]

COURSE_CHOICES = [
    ('B.tech', 'B.tech')
]

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    enrollment_number = models.CharField(max_length=50, unique=True)
    batch_year = models.IntegerField()
    branch = models.CharField(max_length=100, choices=BRANCH_CHOICES, default='Computer science engineering')
    course_name = models.CharField(max_length=50, choices=COURSE_CHOICES, default='B.tech')
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    section = models.CharField(max_length=50, null=True, blank=True)
    attendance_risk = models.BooleanField(default=False)

    @property
    def current_semester(self):
        from datetime import date
        today = date.today()
        # Assume academic year starts in July/August.
        years_diff = today.year - self.batch_year
        if today.month >= 7:
            sem = years_diff * 2 + 1
        else:
            sem = years_diff * 2
        
        sem = max(1, sem)
        if sem == 1:
            return "1st Semester"
        elif sem == 2:
            return "2nd Semester"
        elif sem == 3:
            return "3rd Semester"
        else:
            return f"{sem}th Semester"

    @property
    def current_year(self):
        sem = int(''.join(filter(str.isdigit, self.current_semester)))
        year = (sem + 1) // 2
        return f"{year}rd Year" if year == 3 else f"{year}th Year" if year > 3 else f"{year}nd Year" if year == 2 else "1st Year"

    def __str__(self):
        return f"{self.user.name} ({self.enrollment_number})"

class Course(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)
    credits = models.IntegerField(default=3)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    semester = models.CharField(max_length=50, choices=SEMESTER_CHOICES)
    date_enrolled = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.name} enrolled in {self.course.code}"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendance_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    lecture_number = models.IntegerField(choices=[(i, str(i)) for i in range(1, 8)], default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')

    class Meta:
        unique_together = ('student', 'course', 'date', 'lecture_number')

    def __str__(self):
        return f"{self.student.user.name} - {self.course.code} - {self.date} (L{self.lecture_number}): {self.status}"

class FeeRecord(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
        ('Overdue', 'Overdue'),
    ]
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='fee_records')
    semester = models.CharField(max_length=50, choices=SEMESTER_CHOICES)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    @property
    def remaining_amount(self):
        return self.amount_due - self.amount_paid

    def __str__(self):
        return f"{self.student.user.name} - {self.semester} Fee: {self.status}"

class AcademicRecord(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='academic_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.CharField(max_length=50, choices=SEMESTER_CHOICES)
    grade = models.CharField(max_length=5)
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.student.user.name} - {self.course.code} ({self.semester}): {self.grade}"

class AttendanceMonitoringLog(models.Model):
    date_performed = models.DateTimeField(auto_now_add=True)
    students_analyzed = models.IntegerField(default=0)
    students_at_risk = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    reports_generated = models.IntegerField(default=0)
    summary_insight = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Monitoring Log - {self.date_performed.date()}"

class AttendanceIntervention(models.Model):
    log = models.ForeignKey(AttendanceMonitoringLog, on_delete=models.CASCADE, related_name='interventions')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    overall_attendance = models.DecimalField(max_digits=5, decimal_places=2)
    notification_sent = models.BooleanField(default=False)
    date_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Intervention for {self.student.enrollment_number} on {self.log.date_performed.date()}"
