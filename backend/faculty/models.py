from django.db import models
from authentication.models import User
from backend.student.models import Course, SEMESTER_CHOICES, BRANCH_CHOICES

class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class FacultyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_module_profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='faculties')
    designation = models.CharField(max_length=100, default="Assistant Professor")
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    date_joined = models.DateField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.user.role != 'faculty':
            raise ValidationError("The associated user must have the 'faculty' role.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.name} ({self.department.code if self.department else 'N/A'})"


class FacultyCourseAssignment(models.Model):
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='course_assignments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assigned_faculties')
    semester = models.CharField(max_length=50, choices=SEMESTER_CHOICES)

    class Meta:
        unique_together = ('faculty', 'course', 'semester')
        verbose_name = 'Faculty Course Specialization'
        verbose_name_plural = 'Faculty Course Specializations'

    def __str__(self):
        return f"{self.faculty.user.name} - Specializes in {self.course.code} ({self.semester})"

class Assignment(models.Model):
    SUBMISSION_MODE_CHOICES = [
        ('online', 'Online (via Portal)'),
        ('offline', 'Offline (Physical Submission)'),
    ]
    title = models.CharField(max_length=250)
    description = models.TextField(null=True, blank=True)
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='given_assignments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_assignments')
    branch = models.CharField(max_length=100, choices=BRANCH_CHOICES)
    year = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_datetime = models.DateTimeField(null=True, blank=True, verbose_name="Due Date & Time")
    attachment = models.FileField(upload_to='assignments/materials/', null=True, blank=True, help_text="Upload instructions/notes in PDF or Word format")
    submission_mode = models.CharField(max_length=10, choices=SUBMISSION_MODE_CHOICES, default='online', verbose_name="Submission Mode")
    # AI Evaluation Settings
    enable_ai_evaluation = models.BooleanField(default=False, help_text="Enable automatic AI grading after deadline")
    max_marks = models.IntegerField(default=10, help_text="Maximum marks for AI evaluation (e.g., 10, 20, 50, 100)")
    rubric = models.TextField(null=True, blank=True, help_text="Optional answer key or marking scheme for AI to reference during evaluation")

    def __str__(self):
        return self.title

class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('student.StudentProfile', on_delete=models.CASCADE, related_name='submissions')
    content = models.TextField(null=True, blank=True, help_text="Submission notes")
    attachment = models.FileField(upload_to='assignments/submissions/', null=True, blank=True, help_text="Upload your work in PDF or Word format")
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=10, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    ai_confidence = models.CharField(max_length=10, null=True, blank=True, help_text="AI evaluation confidence: high, medium, or low")

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"{self.student.user.name} - {self.assignment.title}"

class SectionCoordinator(models.Model):
    branch = models.CharField(max_length=100, choices=BRANCH_CHOICES)
    section = models.CharField(max_length=50)
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='coordinated_sections')

    class Meta:
        unique_together = ('branch', 'section')

    def __str__(self):
        return f"{self.section} Coordinator: {self.faculty.user.name}"

class AssignmentReminderLog(models.Model):
    REMINDER_TYPES = [
        ('50', '50% Duration'),
        ('75', '75% Duration'),
        ('90', '90% Duration'),
        ('day_morning', 'Submission Day Morning'),
        ('day_evening', 'Submission Day Evening'),
        ('final', '3 Hours Before Deadline'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='reminder_logs')
    student = models.ForeignKey('student.StudentProfile', on_delete=models.CASCADE, related_name='assignment_reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('assignment', 'student', 'reminder_type')

    def __str__(self):
        return f"{self.reminder_type} reminder for {self.student.user.name} - {self.assignment.title}"

class FacultyAssignmentReportLog(models.Model):
    REPORT_STAGES = [
        ('50', '50% Milestone'),
        ('75', '75% Milestone'),
        ('90', '90% Milestone'),
        ('final', 'Final Deadline Report'),
    ]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='faculty_report_logs')
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='assignment_reports')
    report_stage = models.CharField(max_length=10, choices=REPORT_STAGES)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('assignment', 'faculty', 'report_stage')

    def __str__(self):
        return f"{self.report_stage} report for {self.faculty.user.name} - {self.assignment.title}"

class SubjectNote(models.Model):
    title = models.CharField(max_length=250)
    description = models.TextField(null=True, blank=True)
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='uploaded_notes')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_notes')
    branch = models.CharField(max_length=100, choices=BRANCH_CHOICES)
    year = models.CharField(max_length=20, null=True, blank=True)
    file = models.FileField(upload_to='notes/materials/', help_text="Upload notes in PDF, DOCX, or PPT format")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.course.code}"

class AssignmentEvaluationLog(models.Model):
    assignment = models.OneToOneField(Assignment, on_delete=models.CASCADE, related_name='evaluation_log')
    evaluated_at = models.DateTimeField(auto_now_add=True)
    total_evaluated = models.IntegerField(default=0)
    report_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Evaluation for {self.assignment.title} at {self.evaluated_at}"
