from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Fixes the database migration state'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # First, check if we have the migrations table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='django_migrations'
            """)
            if not cursor.fetchone():
                self.stdout.write('Creating migrations table...')
                call_command('migrate', '--run-syncdb')
                return

            # Remove problematic migrations
            self.stdout.write('Removing problematic migrations...')
            cursor.execute("""
                DELETE FROM django_migrations 
                WHERE app IN ('sites', 'socialaccount')
            """)
            
            # Now run migrations in the correct order
            self.stdout.write('Running migrations in correct order...')
            
            # First migrate auth and contenttypes
            call_command('migrate', 'auth', verbosity=1)
            call_command('migrate', 'contenttypes', verbosity=1)
            
            # Then migrate sites
            call_command('migrate', 'sites', verbosity=1)
            
            # Then migrate socialaccount
            call_command('migrate', 'socialaccount', verbosity=1)
            
            # Finally migrate everything else
            call_command('migrate', verbosity=1)
            
            self.stdout.write(self.style.SUCCESS('Successfully fixed database state')) 