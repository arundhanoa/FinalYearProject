from django.core.management.base import BaseCommand
from recommendations.services import ContentBasedRecommender

class Command(BaseCommand):
    help = 'Update event similarities for content-based recommendations'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting similarity computation...')
        recommender = ContentBasedRecommender()
        recommender.compute_event_similarities()
        self.stdout.write(self.style.SUCCESS('Successfully updated event similarities')) 