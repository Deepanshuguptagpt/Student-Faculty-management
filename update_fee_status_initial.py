
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import StudentProfile, FeeRecord

def update_fee_statuses():
    unpaid_enrollments = [
        "0818CL231032",
        "0818CL231023",
        "0818CL231020",
        "0818CL231007",
        "0818CL231036",
        "0818CL231031",
        "0818CL231064",
        "0818CL231072",
        "0818CL231076",
    ]
    
    print("Updating fee statuses for all students...")
    
    # Process all students
    all_students = StudentProfile.objects.all()
    count_paid = 0
    count_unpaid = 0
    
    for student in all_students:
        # Get all fee records for this student
        fee_records = FeeRecord.objects.filter(student=student)
        
        is_unpaid_target = student.enrollment_number in unpaid_enrollments
        
        for record in fee_records:
            if is_unpaid_target:
                # Keep as Pending/Overdue if it's one of the target students
                # Ensure it's not marked as Paid
                if record.status == 'Paid':
                    record.status = 'Pending'
                    record.amount_paid = 0.00 # Or some partial amount, but let's go with 0 for now as requested "not paid"
                count_unpaid += 1
            else:
                # Mark as Paid for everyone else
                record.status = 'Paid'
                record.amount_paid = record.amount_due
                count_paid += 1
            record.save()
            
    print(f"Updated {count_paid} records to 'Paid' and ensured {count_unpaid} records reflect 'Unpaid' status for target students.")

if __name__ == "__main__":
    update_fee_statuses()
