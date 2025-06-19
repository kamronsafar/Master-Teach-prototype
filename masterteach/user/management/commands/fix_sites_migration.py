from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Fixes the sites migration issue'

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        
        # First, remove all migrations
        self.stdout.write('Removing all migrations...')
        recorder.migration_qs.all().delete()
        
        self.stdout.write(self.style.SUCCESS('Successfully removed all migrations'))
        
        # Now run migrations in the correct order
        self.stdout.write('Running migrations in correct order...')
        
        # First migrate auth and contenttypes (required by sites)
        call_command('migrate', 'auth', verbosity=1)
        call_command('migrate', 'contenttypes', verbosity=1)
        
        # Then migrate sites
        call_command('migrate', 'sites', verbosity=1)
        
        # Then migrate socialaccount
        call_command('migrate', 'socialaccount', verbosity=1)
        
        # Finally migrate everything else
        call_command('migrate', verbosity=1)
        
        self.stdout.write(self.style.SUCCESS('Successfully reset and reapplied migrations')) 