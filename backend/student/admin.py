from django.contrib import admin
from .models import (
    StudentProfile, Course, Enrollment, Attendance,
    FeeRecord, AcademicRecord, AttendanceMonitoringLog, AttendanceIntervention
)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'enrollment_number', 'branch', 'batch_year', 'section')
    search_fields = ('user__name', 'user__email', 'enrollment_number')
    list_filter = ('branch', 'batch_year', 'section')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'credits')
    search_fields = ('code', 'name')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'semester', 'date_enrolled')
    list_filter = ('semester',)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'date', 'lecture_number', 'status')
    list_filter = ('status', 'date')
    search_fields = ('student__user__name', 'course__code')

@admin.register(FeeRecord)
class FeeRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'amount_due', 'amount_paid', 'status', 'due_date')
    list_filter = ('status', 'semester')

@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'semester', 'grade', 'marks')

@admin.register(AttendanceMonitoringLog)
class AttendanceMonitoringLogAdmin(admin.ModelAdmin):
    list_display = ('date_performed', 'students_analyzed', 'students_at_risk', 'emails_sent')
