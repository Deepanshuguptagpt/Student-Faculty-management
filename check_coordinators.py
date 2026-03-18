
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from backend.faculty.models import SectionCoordinator

def check_coordinators():
    coordinators = SectionCoordinator.objects.all()
    if not coordinators.exists():
        print("No section coordinators found in the database!")
    else:
        print(f"Found {coordinators.count()} section coordinators:")
        for coord in coordinators:
            print(f"Section: {coord.section}, Branch: {coord.branch}, Faculty: {coord.faculty.user.name}")

if __name__ == "__main__":
    check_coordinators()
