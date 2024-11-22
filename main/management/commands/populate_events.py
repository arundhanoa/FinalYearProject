from django.core.management.base import BaseCommand
from main.models import Event, User, Recommendation, EventSignUp
from datetime import date, time
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Populate the Event, Recommendation, and EventSignUp models with fake data'

    def handle(self, *args, **kwargs):
        # Create default user
        default_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            default_user.set_password('admin123')
            default_user.save()

        fake = Faker()

        # Create initial sample event
        event = Event.objects.create(
            title="Sample Event",
            description="This is a sample event description",
            date=date.today(),
            time=time(14, 0),
            location_type="Virtual",
            virtual_link=fake.url(),
            capacity=50,
            line_of_service="Sample Service",
            price_type="free",
            creator=default_user
        )

        # Create fake events
        for _ in range(10):
            event = Event.objects.create(
                title=fake.company(),
                description=fake.text(max_nb_chars=500),
                date=fake.date_this_year(),
                time=fake.time_object(),
                location_type=random.choice(['Virtual', 'In-person', 'Hybrid']),
                location=fake.address() if random.choice(['In-person', 'Hybrid']) else None,
                virtual_link=fake.url() if random.choice(['Virtual', 'Hybrid']) else None,
                capacity=random.randint(10, 100),
                line_of_service=random.choice(['Tax', 'Audit', 'Consulting', 'Deals']),
                price_type=random.choice(['free', 'self-funded', 'paid']),
                cost=random.uniform(10, 100) if random.choice(['self-funded', 'paid']) else None,
                creator=default_user
            )

            # Create recommendations
            for _ in range(random.randint(1, 5)):
                Recommendation.objects.create(
                    event=event,
                    user=default_user,
                    score=random.uniform(1, 5)
                )

            # Create event sign-ups
            EventSignUp.objects.create(
                user=default_user,
                event=event
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully created event: {event.title}'))

