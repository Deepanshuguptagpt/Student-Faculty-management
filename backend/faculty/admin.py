from django.contrib import admin
from .models import Department, FacultyProfile, FacultyCourseAssignment, SectionCoordinator

@admin.register(SectionCoordinator)
class SectionCoordinatorAdmin(admin.ModelAdmin):
    list_display = ('branch', 'section', 'faculty')
    list_filter = ('branch', 'section')
    search_fields = ('section', 'faculty__user__name')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'designation', 'contact_number')
    search_fields = ('user__name', 'user__email', 'department__name')
    list_filter = ('department',)

@admin.register(FacultyCourseAssignment)
class FacultyCourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('faculty', 'course', 'semester')
    search_fields = ('faculty__user__name', 'course__name', 'semester')
    list_filter = ('semester', 'course')
