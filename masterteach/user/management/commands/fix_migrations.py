from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fixes migration inconsistency by removing and recreating migrations'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Remove existing migrations
            cursor.execute("DELETE FROM django_migrations WHERE app = 'socialaccount'")
            cursor.execute("DELETE FROM django_migrations WHERE app = 'sites'")
            self.stdout.write(self.style.SUCCESS('Successfully removed existing migrations'))
            
        self.stdout.write(self.style.SUCCESS('Now run: python manage.py migrate sites zero'))
        self.stdout.write(self.style.SUCCESS('Then run: python manage.py migrate socialaccount zero'))
        self.stdout.write(self.style.SUCCESS('Finally run: python manage.py migrate')) 