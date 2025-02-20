from django.core.management.base import BaseCommand
from main.models import Event, CustomUser
from recommendations.models import UserEventInteraction
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up incorrect event signup relationships'

    def handle(self, *args, **kwargs):
        # Get all events with attendees
        events = Event.objects.filter(attendees__isnull=False).distinct()
        
        cleaned = 0
        for event in events:
            # Get all interactions for this event
            valid_signups = UserEventInteraction.objects.filter(
                event=event,
                interaction_type='signup'
            ).values_list('user_id', flat=True)
            
            # Get current attendees that don't have a signup interaction
            invalid_attendees = event.attendees.exclude(id__in=valid_signups)
            
            if invalid_attendees.exists():
                count = invalid_attendees.count()
                # Remove invalid attendees
                event.attendees.remove(*invalid_attendees)
                cleaned += count
                logger.info(f"Removed {count} invalid attendees from event {event.id}: {event.title}")
        
        self.stdout.write(self.style.SUCCESS(f"Cleaned up {cleaned} invalid event signups")) 