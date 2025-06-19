from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

class Command(BaseCommand):
    help = 'Resets migrations for sites and socialaccount apps'

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        
        # First, remove socialaccount migrations
        self.stdout.write('Removing socialaccount migrations...')
        recorder.migration_qs.filter(app='socialaccount').delete()
        
        # Then remove sites migrations
        self.stdout.write('Removing sites migrations...')
        recorder.migration_qs.filter(app='sites').delete()
        
        self.stdout.write(self.style.SUCCESS('Successfully removed migrations'))
        
        # Now run migrations in correct order
        self.stdout.write('Running migrations in correct order...')
        from django.core.management import call_command
        
        # First migrate sites
        call_command('migrate', 'sites', verbosity=1)
        # Then migrate socialaccount
        call_command('migrate', 'socialaccount', verbosity=1)
        # Finally migrate everything else
        call_command('migrate', verbosity=1)
        
        self.stdout.write(self.style.SUCCESS('Successfully reset and reapplied migrations')) 