from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import StudentProfile, Course, Enrollment, Attendance, FeeRecord, AcademicRecord

def get_student_profile(request):
    """Helper method to get the current student profile from session."""
    student_email = request.session.get('student_email')
    if student_email:
        return StudentProfile.objects.filter(user__email=student_email).first()
    return StudentProfile.objects.first() # Fallback for demo


def student_dashboard(request):
    try:
        student_profile = get_student_profile(request)
        if not student_profile:
             return render(request, "dashboards/student/overview.html", {"error": "No student profile found for this user."})

        enrollments = Enrollment.objects.filter(student=student_profile)
        attendance_records = Attendance.objects.filter(student=student_profile)
        fee_records = FeeRecord.objects.filter(student=student_profile)
        academic_records = AcademicRecord.objects.filter(student=student_profile)

        total_attendance = attendance_records.count()
        present_count = attendance_records.filter(status='Present').count()
        attendance_percentage = (present_count / total_attendance * 100) if total_attendance > 0 else 0

        total_due = sum(fee.amount_due for fee in fee_records if fee.status != 'Paid')
        total_paid = sum(fee.amount_paid for fee in fee_records)

        context = {
            'profile': student_profile,
            'enrollments': enrollments,
            'attendance_percentage': round(attendance_percentage, 1),
            'attendance_records': attendance_records[:5],
            'fee_records': fee_records,
            'total_due': total_due,
            'total_paid': total_paid,
            'academic_records': academic_records
        }
        return render(request, "dashboards/student/overview.html", context)
    except Exception as e:
        return render(request, "dashboards/student/overview.html", {"error": str(e)})

def student_attendance(request):
    profile = get_student_profile(request)
    records = Attendance.objects.filter(student=profile).order_by('-date')
    return render(request, "dashboards/student/attendance.html", {'profile': profile, 'records': records})

def student_fees(request):
    profile = get_student_profile(request)
    records = FeeRecord.objects.filter(student=profile)
    total_due = sum(fee.amount_due for fee in records if fee.status != 'Paid')
    return render(request, "dashboards/student/fees.html", {'profile': profile, 'records': records, 'total_due': total_due})

def student_courses(request):
    profile = get_student_profile(request)
    records = Enrollment.objects.filter(student=profile)
    return render(request, "dashboards/student/courses.html", {'profile': profile, 'records': records})

def student_academics(request):
    profile = get_student_profile(request)
    records = AcademicRecord.objects.filter(student=profile)
    return render(request, "dashboards/student/academics.html", {'profile': profile, 'records': records})