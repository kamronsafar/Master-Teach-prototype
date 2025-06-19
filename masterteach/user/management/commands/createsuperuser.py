from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser with email and password'

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS('Superuser already exists'))
            return

        email = input('Email address: ')
        password = input('Password: ')
        password_confirm = input('Password (again): ')

        if password != password_confirm:
            self.stdout.write(self.style.ERROR('Passwords do not match'))
            return

        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    email=email,
                    username=email,  # Using email as username
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(f'Superuser {email} created successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}')) 