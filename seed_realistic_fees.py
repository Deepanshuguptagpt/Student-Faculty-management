
import os
import django
import random
from datetime import date

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.student.models import StudentProfile, FeeRecord

def get_sem_str(i):
    suffix = "th"
    if i == 1: suffix = "st"
    elif i == 2: suffix = "nd"
    elif i == 3: suffix = "rd"
    return f"{i}{suffix} Semester"

def seed_realistic_fees():
    print("Clearing old fee records...")
    FeeRecord.objects.all().delete()
    
    students = StudentProfile.objects.all()
    print(f"Processing {students.count()} students...")
    
    current_year_now = date.today().year
    current_month_now = date.today().month
    
    records_created = 0
    
    for student in students:
        # Calculate current semester integer
        years_diff = current_year_now - student.batch_year
        if current_month_now >= 7:
            current_sem_int = years_diff * 2 + 1
        else:
            current_sem_int = years_diff * 2
        
        current_sem_int = max(1, min(8, current_sem_int))
        
        # 1. Handle previous semesters (All Paid)
        for i in range(1, current_sem_int):
            sem_str = get_sem_str(i)
            FeeRecord.objects.create(
                student=student,
                semester=sem_str,
                amount_due=60000.00,
                amount_paid=60000.00,
                due_date=date(student.batch_year + (i//2), 6 if i%2==0 else 12, 30 if i%2==0 else 31),
                status='Paid'
            )
            records_created += 1
            
        # 2. Handle current semester (Randomized)
        sem_str = get_sem_str(current_sem_int)
        
        # Random choice: 0 = Unpaid, 1 = Partial, 2 = Fully Paid
        choice = random.choices([0, 1, 2], weights=[40, 30, 30])[0]
        
        if choice == 0:
            paid = 0
            status = 'Pending'
        elif choice == 1:
            paid = random.randint(1000, 50000)
            status = 'Pending'
        else:
            paid = 60000
            status = 'Paid'
            
        FeeRecord.objects.create(
            student=student,
            semester=sem_str,
            amount_due=60000.00,
            amount_paid=paid,
            due_date=date(2026, 6, 30) if current_sem_int % 2 == 0 else date(2026, 12, 31),
            status=status
        )
        records_created += 1

    print(f"Successfully created {records_created} realistic fee records.")

if __name__ == "__main__":
    seed_realistic_fees()
