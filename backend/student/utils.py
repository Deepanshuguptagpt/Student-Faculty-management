from datetime import datetime
from .models import Enrollment, Attendance
from backend.faculty.models import FacultyCourseAssignment

def calculate_detailed_attendance(profile, start_date=None, end_date=None):
    """
    Core logic for calculating student attendance, reused from the dashboard.
    Returns:
        {
            'global_theory_pct': float,
            'global_practical_pct': float,
            'global_overall_pct': float,
            'course_data': list of dicts,
        }
    """
    # Base query for attendance
    attendance_qs = Attendance.objects.filter(student=profile)
    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        attendance_qs = attendance_qs.filter(date__gte=start_date)
    if end_date:
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        attendance_qs = attendance_qs.filter(date__lte=end_date)

    # Get all enrolled courses to group them
    enrollments = Enrollment.objects.filter(student=profile).select_related('course')
    
    # Grouping logic: Group by base code (e.g., AL-602 and AL-602[P])
    course_groups = {}
    
    for en in enrollments:
        course = en.course
        base_code = course.code.replace('[P]', '')
        
        if base_code not in course_groups:
            # Find faculty for the theory part primarily, or whatever is available
            # Added select_related for performance and safer access
            faculty_assignment = FacultyCourseAssignment.objects.filter(
                course__code__icontains=base_code
            ).select_related('faculty__user').first()
            
            faculty_name = "TBD"
            if faculty_assignment and faculty_assignment.faculty and hasattr(faculty_assignment.faculty, 'user'):
                faculty_name = faculty_assignment.faculty.user.name
            
            course_groups[base_code] = {
                'name': course.name.replace(' Lab', '').replace(' practical', ''),
                'base_code': base_code,
                'faculty': faculty_name,
                'theory': {'total': 0, 'present': 0, 'absent': 0, 'records': []},
                'practical': {'total': 0, 'present': 0, 'absent': 0, 'records': []},
                'total_all': 0,
                'present_all': 0,
            }
        
        # Determine if theory or practical
        is_practical = '[P]' in course.code
        category = 'practical' if is_practical else 'theory'
        
        # Get attendance for this specific course variation
        course_attendance = attendance_qs.filter(course=course).order_by('-date')
        
        course_groups[base_code][category]['total'] += course_attendance.count()
        course_groups[base_code][category]['present'] += course_attendance.filter(status='Present').count()
        course_groups[base_code][category]['absent'] += course_attendance.filter(status='Absent').count()
        
        # Merge records for detailed view
        for att in course_attendance:
            course_groups[base_code][category]['records'].append(att)
            course_groups[base_code]['total_all'] += 1
            if att.status == 'Present':
                course_groups[base_code]['present_all'] += 1

    # Calculate global indicators
    total_theory = 0
    present_theory = 0
    total_practical = 0
    present_practical = 0
    
    course_data_list = []
    for base_code, data in course_groups.items():
        total_theory += data['theory']['total']
        present_theory += data['theory']['present']
        total_practical += data['practical']['total']
        present_practical += data['practical']['present']
        
        # Calculate individual course percentage
        total = data['total_all']
        present = data['present_all']
        data['percentage'] = (present / total * 100) if total > 0 else 0
        
        # Sort records by date for the detailed view
        all_records = data['theory']['records'] + data['practical']['records']
        data['all_records'] = sorted(all_records, key=lambda x: x.date, reverse=True)
        
        course_data_list.append(data)

    global_theory_pct = (present_theory / total_theory * 100) if total_theory > 0 else 0
    global_practical_pct = (present_practical / total_practical * 100) if total_practical > 0 else 0
    
    total_overall = total_theory + total_practical
    present_overall = present_theory + present_practical
    global_overall_pct = (present_overall / total_overall * 100) if total_overall > 0 else 0

    return {
        'global_theory_pct': round(global_theory_pct, 1),
        'global_practical_pct': round(global_practical_pct, 1),
        'global_overall_pct': round(global_overall_pct, 1),
        'course_data': course_data_list,
        'total_theory': total_theory,
        'present_theory': present_theory,
        'total_practical': total_practical,
        'present_practical': present_practical,
    }
