import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from authentication.models import User

def main():
    print("Fixing student login issues...")
    
    # Update all student passwords to "password123"
    updated_passwords = User.objects.filter(role='student').update(password='password123')
    print(f"Updated {updated_passwords} student passwords to 'password123'.")
    
    # Verify a few samples
    samples = User.objects.filter(role='student')[:3]
    print("\nSample Student Access Info:")
    for s in samples:
        print(f"Email: {s.email}, Password: {s.password}")

if __name__ == "__main__":
    main()
