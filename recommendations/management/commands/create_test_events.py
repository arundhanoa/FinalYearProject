from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Event, Tag, CustomUser
from datetime import timedelta
from faker import Faker
import random
from django.core.files.base import ContentFile
import requests
import os
from django.contrib.auth.models import get_user_model

class Command(BaseCommand):
    help = 'Creates realistic test events using Faker'

    def __init__(self):
        super().__init__()
        self.fake = Faker()
        
        # Define service-specific tags and titles
        self.service_data = {
            'Audit': {
                'tags': [
                    'Financial Audit', 'Risk Assessment', 'Internal Controls',
                    'Compliance', 'IFRS', 'GAAP', 'SOX', 'Regulatory Reporting',
                    'Audit Analytics', 'Quality Assurance'
                ],
                'title_prefixes': [
                    'Financial Statement Analysis', 'Audit Methodology',
                    'Risk-Based Auditing', 'Internal Controls Workshop',
                    'Compliance Training'
                ]
            },
            'Tax': {
                'tags': [
                    'Tax Planning', 'International Tax', 'Corporate Tax',
                    'VAT', 'Tax Compliance', 'Transfer Pricing',
                    'Tax Technology', 'Tax Analytics', 'Tax Advisory'
                ],
                'title_prefixes': [
                    'Tax Strategy Workshop', 'International Tax Planning',
                    'Corporate Tax Updates', 'Tax Technology Innovation',
                    'Tax Compliance Training'
                ]
            },
            'Consulting': {
                'tags': [
                    'Strategy', 'Digital Transformation', 'Change Management',
                    'Process Improvement', 'Innovation', 'Business Analysis',
                    'Project Management', 'Agile', 'Design Thinking'
                ],
                'title_prefixes': [
                    'Digital Strategy', 'Business Transformation',
                    'Innovation Workshop', 'Change Management',
                    'Process Excellence'
                ]
            },
            'Advisory': {
                'tags': [
                    'Risk Management', 'Cybersecurity', 'Data Analytics',
                    'AI/ML', 'Blockchain', 'Cloud Computing', 'ESG',
                    'Sustainability', 'Digital Risk'
                ],
                'title_prefixes': [
                    'Risk Advisory', 'Technology Innovation',
                    'Digital Security', 'Data Analytics',
                    'Sustainability Strategy'
                ]
            },
            'Assurance': {
                'tags': [
                    'Quality Assurance', 'Process Assurance', 'IT Assurance',
                    'Financial Reporting', 'Controls Testing', 'Regulatory Compliance',
                    'Standards & Controls'
                ],
                'title_prefixes': [
                    'Quality Assurance', 'Process Controls',
                    'IT Systems Assurance', 'Regulatory Compliance',
                    'Control Framework'
                ]
            },
            'All': {
                'tags': [
                    'Leadership', 'Professional Development', 'Networking',
                    'Soft Skills', 'Communication', 'Team Building',
                    'Career Development', 'Industry Trends'
                ],
                'title_prefixes': [
                    'Professional Development', 'Leadership Excellence',
                    'Industry Insights', 'Networking Event',
                    'Career Growth'
                ]
            }
        }

    def get_random_image(self):
        """Get a random business/tech themed image"""
        # Use business-specific categories
        categories = ['business', 'technology', 'office', 'meeting']
        width, height = 800, 600
        
        try:
            # Try unsplash for better business images
            response = requests.get(
                f'https://source.unsplash.com/random/{width}x{height}/?{random.choice(categories)}',
                timeout=5
            )
            if response.status_code == 200:
                filename = f'event_{self.fake.uuid4()}.jpg'
                self.stdout.write(f'Downloaded image: {filename}')
                return ContentFile(response.content, name=filename)
        except Exception as e:
            self.stdout.write(f'Failed to get image: {str(e)}')
        return None

    def create_event(self, service, admin_user, tags):
        """Create a single event with coherent service, tags, and title"""
        service_info = self.service_data[service]
        
        # Get service-specific tags plus some general ones
        service_tags = random.sample(service_info['tags'], k=min(3, len(service_info['tags'])))
        general_tags = random.sample(self.service_data['All']['tags'], k=2)
        event_tags = [Tag.objects.get_or_create(name=tag)[0] for tag in service_tags + general_tags]
        
        # Create coherent title
        title_prefix = random.choice(service_info['title_prefixes'])
        title_suffix = self.fake.catch_phrase()
        title = f"{title_prefix}: {title_suffix}"
        
        event = Event.objects.create(
            title=title,
            description=self.fake.paragraph(nb_sentences=5),
            date=self.fake.date_between(start_date='+1d', end_date='+90d'),
            time=self.fake.time(),
            location_type=random.choice(['virtual', 'in-person', 'hybrid']),
            price_type=random.choice(['free', 'paid-for', 'self-funded']),
            line_of_service=service,
            creator=admin_user,
            duration=random.choice([60, 90, 120, 180]),
            cost=random.choice([0, 25, 50, 100]),
            capacity=random.randint(20, 200)
        )
        
        # Add tags
        event.tags.set(event_tags)
        
        # Add image
        image = self.get_random_image()
        if image:
            event.image = image
            event.save()
            
        return event

    def handle(self, *args, **kwargs):
        # Add at start of handle method
        if not os.path.exists('media/event_images'):
            os.makedirs('media/event_images')

        # Create admin if doesn't exist
        admin_user = CustomUser.objects.filter(is_staff=True).first()
        if not admin_user:
            admin_user = CustomUser.objects.create_superuser(
                username='admin',
                password='admin123',
                work_email='admin@test.com',
                workday_id='WD_ADMIN',
                line_of_service='All'
            )

        # Create events
        for i in range(75):
            # Ensure even distribution across services
            service = list(self.service_data.keys())[i % len(self.service_data)]
            event = self.create_event(service, admin_user, self.service_data)
            self.stdout.write(f'Created event {i+1}/75: {event.title} ({service})') 