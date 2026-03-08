from backend.student.models import StudentProfile, Enrollment, FeeRecord, AcademicRecord
from backend.faculty.models import FacultyCourseAssignment
from datetime import date

today = date.today()
for model in [Enrollment, FeeRecord, AcademicRecord]:
    for record in model.objects.all():
        student = record.student
        years = today.year - student.batch_year
        sem = years * 2 + (1 if today.month >= 7 else 0)
        sem = max(1, sem)
        if sem == 1: str_sem = '1st Semester'
        elif sem == 2: str_sem = '2nd Semester'
        elif sem == 3: str_sem = '3rd Semester'
        else: str_sem = f'{sem}th Semester'
        record.semester = str_sem
        record.save()

FacultyCourseAssignment.objects.update(semester='1st Semester')
print('DONE')
