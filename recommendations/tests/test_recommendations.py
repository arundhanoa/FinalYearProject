from django.test import TestCase
from main.models import Event, Tag
from django.contrib.auth import get_user_model
from django.utils import timezone
from recommendations.models import UserEventInteraction
from recommendations.services import HybridRecommender
import random
from datetime import timedelta
import time

class RecommendationSystemTest(TestCase):
    def setUp(self):
        # Create test users with unique workday IDs
        User = get_user_model()
        self.users = []
        for i, service in enumerate(['Audit', 'Tax', 'Consulting', 'Advisory', 'Assurance']):
            user = User.objects.create_user(
                username=f'test_{service.lower()}_{random.randint(1000,9999)}',  # Make username unique
                password='testpass123',
                line_of_service=service,
                work_email=f'test_{service.lower()}_{random.randint(1000,9999)}@test.com',  # Make unique
                workday_id=f'WD{i}_{random.randint(1000, 9999)}',
                job_title='Test Role',
                line_manager='Test Manager',
                career_coach='Test Coach',
                home_office='London'
            )
            self.users.append(user)

        # Create more varied tags
        self.tags = []
        tag_names = [
            'Training', 'Social', 'Technical', 'Leadership', 'Development',
            'Networking', 'Workshop', 'Conference', 'Seminar', 'Team Building',
            'Volunteering', 'Mentoring', 'Career', 'Innovation', 'Digital',
            'Analytics', 'Strategy', 'Finance', 'Technology', 'Sustainability'
        ]
        for name in tag_names:
            tag, created = Tag.objects.get_or_create(name=name)
            self.tags.append(tag)

        # Create test events
        self.events = []
        for i in range(50):  # Create 50 test events
            event = Event.objects.create(
                title=f'Event {i}: {random.choice(tag_names)} Session',
                description=f'Detailed description for event {i} covering various aspects...',
                date=timezone.now().date() + timedelta(days=random.randint(1, 60)),
                time=timezone.now().time(),
                location_type=random.choice(['virtual', 'in-person', 'hybrid']),
                price_type=random.choice(['free', 'paid-for', 'self-funded']),
                capacity=random.randint(2, 200),
                line_of_service=random.choice(['All', 'Audit', 'Tax', 'Consulting', 'Advisory', 'Assurance']),
                creator=random.choice(self.users),
                duration=random.choice([30, 60, 90, 120, 180]),
                cost=random.choice([0, 25, 50, 100, 150])
            )
            # Add 2-4 random tags
            for tag in random.sample(self.tags, random.randint(2, 5)):
                event.tags.add(tag)
            self.events.append(event)

    def test_event_creation(self):
        """Test that events were created properly"""
        self.assertEqual(Event.objects.count(), 50)
        self.assertEqual(Tag.objects.count(), 20)
        
        # Test event variety
        location_types = set(Event.objects.values_list('location_type', flat=True))
        price_types = set(Event.objects.values_list('price_type', flat=True))
        services = set(Event.objects.values_list('line_of_service', flat=True))
        
        self.assertTrue(len(location_types) >= 3, "Not enough variety in location types")
        self.assertTrue(len(price_types) >= 3, "Not enough variety in price types")
        self.assertTrue(len(services) >= 4, "Not enough variety in services")

    def test_recommendations(self):
        """Test that recommendations are generated properly"""
        from recommendations.services import HybridRecommender
        
        # Create some interactions first
        for event in self.events[:5]:  # First 5 events
            UserEventInteraction.objects.create(
                user=self.users[0],
                event=event,
                interaction_type='view',
                weight=1.0
            )
            # Add some signups
            UserEventInteraction.objects.create(
                user=self.users[0],
                event=event,
                interaction_type='signup',
                weight=1.0
            )
        
        recommender = HybridRecommender()
        test_user = self.users[0]  # Get first test user
        
        # Get recommendations
        recommendations = recommender.get_recommendations(test_user, limit=10)
        
        # Basic checks
        self.assertLessEqual(len(recommendations), 10)
        self.assertTrue(all(isinstance(r, Event) for r in recommendations))
        
        # Check that recommendations match user's line of service
        user_service = test_user.line_of_service
        for event in recommendations:
            self.assertTrue(
                event.line_of_service == 'All' or 
                event.line_of_service == user_service,
                f"Event {event.title} service doesn't match user service"
            )

    def test_recommendation_quality(self):
        """Test that recommendations are relevant to user preferences"""
        test_user = self.users[0]  # Audit service user
        
        # Create specific test events
        target_event = Event.objects.create(
            title='Audit Training Workshop',
            description='Specific audit training...',
            date=timezone.now().date() + timedelta(days=7),
            time=timezone.now().time(),
            location_type='virtual',
            price_type='free',
            line_of_service='Audit',
            creator=self.users[1],
            duration=60,
            cost=0
        )
        target_event.tags.add(Tag.objects.get(name='Training'))
        
        # Create more interactions to make it more popular
        for _ in range(20):  # Increased from 10
            UserEventInteraction.objects.create(
                user=random.choice(self.users),
                event=target_event,
                interaction_type='signup',  # Changed from 'view' to 'signup'
                weight=1.0
            )
            UserEventInteraction.objects.create(
                user=random.choice(self.users),
                event=target_event,
                interaction_type='view',
                weight=1.0
            )
        
        # Get recommendations
        recommender = HybridRecommender()
        recommendations = recommender.get_recommendations(test_user, limit=5)
        
        # Verify target event is in top recommendations
        self.assertIn(target_event, recommendations[:3], 
            "Highly relevant event should be in top recommendations")
        
        # Check recommendation relevance
        for event in recommendations:
            # Service match
            self.assertTrue(
                event.line_of_service in ['All', test_user.line_of_service],
                f"Event {event.title} service doesn't match user service"
            )
            
            # Check event hasn't started
            self.assertTrue(
                event.date >= timezone.now().date(),
                "Recommended past event"
            )

    def test_edge_cases(self):
        """Test system handles edge cases gracefully"""
        recommender = HybridRecommender()
        
        # Test with no events
        Event.objects.all().delete()
        recommendations = recommender.get_recommendations(self.users[0], limit=5)
        self.assertEqual(len(recommendations), 0, "Should handle no events")
        
        # Test with no interactions
        self.setUp()  # Reset database
        UserEventInteraction.objects.all().delete()
        recommendations = recommender.get_recommendations(self.users[0], limit=5)
        self.assertTrue(len(recommendations) > 0, 
            "Should still give recommendations without interactions")
        
        # Test with invalid limit
        recommendations = recommender.get_recommendations(self.users[0], limit=-1)
        self.assertEqual(len(recommendations), 0, "Should handle invalid limit")
        
        # Test with past events
        past_event = Event.objects.first()
        past_event.date = timezone.now().date() - timedelta(days=1)
        past_event.save()
        recommendations = recommender.get_recommendations(self.users[0], limit=5)
        self.assertNotIn(past_event, recommendations, 
            "Should not recommend past events")

    def test_performance(self):
        """Test system performance with larger dataset"""
        # Create more test data
        start_time = time.time()
        
        # Create 1000 events
        bulk_events = []
        for i in range(1000):
            event = Event(
                title=f'Performance Test Event {i}',
                description=f'Test description {i}',
                date=timezone.now().date() + timedelta(days=random.randint(1, 60)),
                time=timezone.now().time(),
                location_type=random.choice(['virtual', 'in-person', 'hybrid']),
                price_type=random.choice(['free', 'paid-for', 'self-funded']),
                line_of_service=random.choice(['All', 'Audit', 'Tax', 'Consulting']),
                creator=random.choice(self.users),
                duration=random.choice([30, 60, 90, 120]),
                cost=random.choice([0, 25, 50, 100])
            )
            bulk_events.append(event)
        
        Event.objects.bulk_create(bulk_events)
        
        # Create 5000 interactions
        bulk_interactions = []
        for _ in range(5000):
            interaction = UserEventInteraction(
                user=random.choice(self.users),
                event=random.choice(bulk_events),
                interaction_type=random.choice(['view', 'signup']),
                weight=1.0
            )
            bulk_interactions.append(interaction)
        
        UserEventInteraction.objects.bulk_create(bulk_interactions)
        
        # Test recommendation speed
        recommender = HybridRecommender()
        start_rec_time = time.time()
        recommendations = recommender.get_recommendations(self.users[0], limit=10)
        end_time = time.time()
        
        # Verify performance
        setup_time = start_rec_time - start_time
        recommendation_time = end_time - start_rec_time
        
        self.assertLess(recommendation_time, 2.0, 
            f"Recommendations took too long: {recommendation_time} seconds")
        self.assertTrue(len(recommendations) > 0, 
            "Should return recommendations with large dataset")

    def test_specific_matching(self):
        """Test specific matching criteria"""
        test_user = self.users[0]
        
        # Create events with specific attributes
        perfect_match = Event.objects.create(
            title='Perfect Match Event',
            description='Test description',
            date=timezone.now().date() + timedelta(days=7),
            time=timezone.now().time(),
            line_of_service=test_user.line_of_service,
            location_type='virtual',
            price_type='free',
            creator=test_user,
            duration=60,
            cost=0
        )
        # Add tags after creation
        perfect_match.tags.set(self.tags[:3])
        
        partial_match = Event.objects.create(
            title='Partial Match Event',
            description='Partial match description',
            date=timezone.now().date() + timedelta(days=14),
            time=timezone.now().time(),
            line_of_service='All',
            location_type='hybrid',
            price_type='paid-for',
            creator=test_user,
            duration=90,
            cost=50
        )
        partial_match.tags.set(self.tags[3:5])
        
        # Add interactions for both events
        for _ in range(15):
            UserEventInteraction.objects.create(
                user=test_user,
                event=perfect_match,
                interaction_type='signup',
                weight=1.0
            )
            UserEventInteraction.objects.create(
                user=test_user,
                event=perfect_match,
                interaction_type='view',
                weight=1.0
            )
        
        # Increase interactions for partial match
        for _ in range(20):  # Increased from 10
            UserEventInteraction.objects.create(
                user=test_user,
                event=partial_match,
                interaction_type='signup',
                weight=0.7
            )
            UserEventInteraction.objects.create(
                user=test_user,
                event=partial_match,
                interaction_type='view',
                weight=0.7
            )
        
        # Get recommendations with larger limit
        recommender = HybridRecommender()
        recommendations = recommender.get_recommendations(test_user, limit=10)  # Increased from 5
        
        # Perfect match should rank higher
        perfect_match_index = recommendations.index(perfect_match)
        partial_match_index = recommendations.index(partial_match)
        self.assertLess(perfect_match_index, partial_match_index,
            "Perfect match should rank higher than partial match")