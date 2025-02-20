from django.core.management.base import BaseCommand
from main.models import Event, Tag
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Clears all test data from the database'

    def handle(self, *args, **kwargs):
        # Delete all events
        event_count = Event.objects.all().delete()[0]
        self.stdout.write(f'Deleted {event_count} events')
        
        # Delete all tags
        tag_count = Tag.objects.all().delete()[0]
        self.stdout.write(f'Deleted {tag_count} tags')
        
        # Delete test admin user
        User = get_user_model()
        admin_count = User.objects.filter(username='admin').delete()[0]
        self.stdout.write(f'Deleted {admin_count} test admin users') 