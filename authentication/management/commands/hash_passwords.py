"""
One-time management command to hash all plaintext passwords.
Safe to run multiple times — skips already-hashed passwords.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password, is_password_usable, identify_hasher
from authentication.models import User


class Command(BaseCommand):
    help = "Hash all existing plaintext passwords using Django's make_password()"

    def handle(self, *args, **options):
        users = User.objects.all()
        hashed_count = 0
        skipped_count = 0

        for user in users:
            # Check if password is already hashed (Django hashed passwords
            # contain a $ separator and start with an algorithm name)
            try:
                identify_hasher(user.password)
                # Already hashed
                skipped_count += 1
                continue
            except ValueError:
                # Not a valid hash — this is a plaintext password
                pass

            original = user.password
            user.password = make_password(original)
            user.save(update_fields=['password'])
            hashed_count += 1
            self.stdout.write(f"  Hashed password for: {user.email}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Hashed: {hashed_count}, Already hashed: {skipped_count}, Total: {users.count()}"
        ))
