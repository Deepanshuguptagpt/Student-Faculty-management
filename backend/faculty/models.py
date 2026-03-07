from django.db import models
from authentication.models import User
from backend.student.models import Course

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
    semester = models.CharField(max_length=50) # e.g., 'Fall 2026'

    class Meta:
        unique_together = ('faculty', 'course', 'semester')

    def __str__(self):
        return f"{self.faculty.user.name} - {self.course.code} ({self.semester})"
