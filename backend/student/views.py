from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import StudentProfile, Course, Enrollment, Attendance, FeeRecord, AcademicRecord
from .utils import calculate_detailed_attendance

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
             return render(request, "dashboards/student/overview_new.html", {"error": "No student profile found for this user."})

        enrollments = Enrollment.objects.filter(student=student_profile)
        attendance_records = Attendance.objects.filter(student=student_profile).order_by('-date')
        fee_records = FeeRecord.objects.filter(student=student_profile)
        academic_records = AcademicRecord.objects.filter(student=student_profile)

        attendance_data = calculate_detailed_attendance(student_profile)

        total_due = sum(fee.amount_due - fee.amount_paid for fee in fee_records if fee.status != 'Paid')
        total_paid = sum(fee.amount_paid for fee in fee_records)

        context = {
            'profile': student_profile,
            'enrollments': enrollments,
            'attendance_percentage': attendance_data['global_overall_pct'],
            'attendance_records': attendance_records[:10],  # Show recent 10
            'fee_records': fee_records,
            'records': academic_records,  # For grades tab
            'total_due': total_due,
            'total_paid': total_paid,
        }
        return render(request, "dashboards/student/overview_new.html", context)
    except Exception as e:
        return render(request, "dashboards/student/overview_new.html", {"error": str(e)})

def student_attendance(request):
    profile = get_student_profile(request)
    if not profile:
        return redirect('login')

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    attendance_data = calculate_detailed_attendance(profile, start_date_str, end_date_str)

    return render(request, "dashboards/student/attendance.html", {
        'profile': profile,
        'global_theory_pct': attendance_data['global_theory_pct'],
        'global_practical_pct': attendance_data['global_practical_pct'],
        'global_overall_pct': attendance_data['global_overall_pct'],
        'course_data': attendance_data['course_data'],
        'start_date': start_date_str,
        'end_date': end_date_str
    })

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
