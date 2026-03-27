from django.db import models

class User(models.Model):

    ROLE_CHOICES = [
        ('student','Student'),
        ('faculty','Faculty'),
        ('admin','Admin')
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    password = models.CharField(max_length=100, default="ADMIN")
    is_active = True

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return self.email