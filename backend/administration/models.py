from django.db import models
from authentication.models import User

class FacultyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.user.name} ({self.employee_id})"
