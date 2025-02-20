from factory import (
    django, 
    Faker as FactoryFaker,
    SubFactory, 
    LazyFunction, 
    LazyAttribute,
    post_generation
)
from factory.fuzzy import FuzzyChoice, FuzzyDateTime
from datetime import datetime, timedelta
from django.utils import timezone
from main.models import Event, Tag
from ..models import UserEventInteraction
from django.contrib.auth import get_user_model
from faker import Faker

# Create Faker instance correctly
fake = Faker()

class TagFactory(django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = FactoryFaker('word')

class EventFactory(django.DjangoModelFactory):
    class Meta:
        model = Event

    title = FactoryFaker('sentence', nb_words=4)
    description = FactoryFaker('paragraph')
    date = LazyFunction(lambda: timezone.now().date() + timedelta(days=fake.random_int(1, 60)))
    time = FactoryFaker('time_object')
    duration = FuzzyChoice([30, 60, 90, 120, 180])
    capacity = FuzzyChoice([10, 20, 50, 100, 200])
    location_type = FuzzyChoice(['virtual', 'in-person', 'hybrid'])
    price_type = FuzzyChoice(['free', 'paid-for', 'self-funded'])
    cost = LazyAttribute(lambda o: 0 if o.price_type == 'free' else fake.random_int(10, 200))
    line_of_service = FuzzyChoice(['All', 'Audit', 'Tax', 'Consulting', 'Advisory'])

    @post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            # Add 2-5 random tags
            num_tags = fake.random_int(2, 5)
            for _ in range(num_tags):
                self.tags.add(TagFactory())

class UserFactory(django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = FactoryFaker('user_name')
    email = FactoryFaker('email')
    line_of_service = FuzzyChoice(['Audit', 'Tax', 'Consulting', 'Advisory'])

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)

class UserEventInteractionFactory(django.DjangoModelFactory):
    class Meta:
        model = UserEventInteraction

    user = SubFactory(UserFactory)
    event = SubFactory(EventFactory)
    interaction_type = FuzzyChoice(['view', 'signup', 'would_signup', 'unregister'])
    timestamp = FuzzyDateTime(
        start_dt=timezone.now() - timedelta(days=30),
        end_dt=timezone.now()
    )
    weight = LazyAttribute(lambda o: {
        'view': 1,
        'signup': 5,
        'would_signup': 4,
        'unregister': -5
    }[o.interaction_type]) 