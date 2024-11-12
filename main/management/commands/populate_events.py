from django.core.management.base import BaseCommand
from main.models import Event, User, Recommendation, EventSignUp
from datetime import date, time
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Populate the Event, Recommendation, and EventSignUp models with fake data'

    def handle(self, *args, **kwargs):
        # 1. First create default user
        default_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            default_user.set_password('admin123')  # Set a default password
            default_user.save()

        # 2. Initialise Faker
        fake = Faker()

        # 3. Create initial sample event
        event = Event.objects.create(
            title="Sample Event",
            line_of_service="Sample Service",
            category="NET",
            description="This is a sample event description",
            location_type="Virtual",
            date=date.today(),
            time=time(14, 0),
            price_type="Free",
            capacity=50,
            created_by=default_user
        )

        # 4. Creating fake data for 10 events (you can change the range as needed)
        for _ in range(10):
            # Event Data
            title = fake.company()  # Fake event title
            line_of_service = fake.job()  # Random line of service (you can adjust this as needed)
            category = random.choice(['TB', 'VOL', 'NET'])  # Random category choice
            description = fake.text(max_nb_chars=500)  # Random description text
            location_type = random.choice(['Virtual', 'In-person', 'Hybrid'])  # Random location type
            location_details = fake.address() if location_type != 'Virtual' else fake.url()  # Location or URL
            event_date = fake.date_this_year()  # Random event date this year
            event_time = fake.time()  # Random time
            price_type = random.choice(['Self-funded', 'Fee', 'Paid for'])  # Random price type
            cost = None
            if price_type != 'Self-funded':
                cost = random.uniform(10, 100)  # Random cost between 10 and 100 (for Fee or Paid for)
            capacity = random.randint(10, 100)  # Random capacity between 10 and 100 people
            created_by = User.objects.order_by('?').first()  # Pick a random user from the User model
            attendees = User.objects.order_by('?')[:random.randint(1, 5)]  # Random attendees from 1 to 5 users
            image = None  # You can use fake.image() if you'd like to populate image URLs

            # Create the event
            event = Event.objects.create(
                title=title,
                line_of_service=line_of_service,
                category=category,
                description=description,
                location_type=location_type,
                location_details=location_details,
                date=event_date,
                time=event_time,
                price_type=price_type,
                cost=cost,
                capacity=capacity,
                created_by=created_by,
                image=image
            )

            # Add attendees to the event
            event.attendees.set(attendees)
            event.save()

            # Create recommendations for each event (optional, for Discover/Popular)
            for attendee in attendees:
                score = random.uniform(1, 5)  # Random score between 1 and 5
                Recommendation.objects.create(
                    event=event,
                    user=attendee,
                    score=score
                )

            # Create event sign-ups for attendees
            for attendee in attendees:
                EventSignUp.objects.create(
                    user=attendee,
                    event=event
                )

            self.stdout.write(self.style.SUCCESS(f'Successfully created event: {title}'))

