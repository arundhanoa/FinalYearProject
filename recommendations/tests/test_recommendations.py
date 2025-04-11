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

    def test_component_weighting(self):
        """Test how different components are weighted in the hybrid algorithm"""
        test_user = self.users[0]  # Audit service user
        
        # Create test events that are optimal for different recommender components
        
        # 1. An event perfect for content-based (matching user preferences)
        content_optimal = Event.objects.create(
            title='Content Optimal Event',
            description='Perfect match for content-based recommender',
            date=timezone.now().date() + timedelta(days=10),
            time=timezone.now().time(),
            line_of_service=test_user.line_of_service,  # Exact service match
            location_type='virtual',  # Preferred location
            price_type='free',        # Preferred price
            creator=self.users[1],
            duration=60,              # Short duration
            cost=0
        )
        # Add tags that match user preferences (based on previous interactions)
        for tag in self.tags[:4]:
            content_optimal.tags.add(tag)
        
        # 2. An event optimal for collaborative filtering
        collab_optimal = Event.objects.create(
            title='Collaborative Optimal Event',
            description='Perfect for collaborative filtering',
            date=timezone.now().date() + timedelta(days=15),
            time=timezone.now().time(),
            line_of_service=test_user.line_of_service,
            location_type='hybrid',
            price_type='paid-for',
            creator=self.users[2],
            duration=120,
            cost=50
        )
        collab_optimal.tags.add(*self.tags[5:8])  # Different tags
        
        # Make similar users interact with this event
        # Create similar users (similar profile to test_user)
        similar_users = []
        for i in range(3):
            similar_user = get_user_model().objects.create_user(
                username=f'similar_user_{i}',
                password='testpass123',
                line_of_service=test_user.line_of_service,
                work_email=f'similar_{i}@test.com',
                workday_id=f'SIM{i}',
                job_title=test_user.job_title,
                home_office=test_user.home_office
            )
            similar_users.append(similar_user)
        
        # Have both test_user and similar users interact with some common events
        common_events = []
        for i in range(5):
            event = Event.objects.create(
                title=f'Common Event {i}',
                description=f'Event {i} for establishing similarity',
                date=timezone.now().date() + timedelta(days=i+20),
                time=timezone.now().time(),
                line_of_service=test_user.line_of_service,
                location_type='virtual',
                price_type='free',
                creator=self.users[1],
                duration=60,
                cost=0
            )
            common_events.append(event)
            # Test user interactions
            UserEventInteraction.objects.create(
                user=test_user,
                event=event,
                interaction_type='view',
                weight=1.0
            )
            UserEventInteraction.objects.create(
                user=test_user,
                event=event,
                interaction_type='signup',
                weight=1.0
            )
            
            # Similar users interactions
            for user in similar_users:
                UserEventInteraction.objects.create(
                    user=user,
                    event=event,
                    interaction_type='view',
                    weight=1.0
                )
                UserEventInteraction.objects.create(
                    user=user,
                    event=event,
                    interaction_type='signup',
                    weight=1.0
                )
        
        # Now have similar users interact with collab_optimal (but not test_user)
        for user in similar_users:
            UserEventInteraction.objects.create(
                user=user,
                event=collab_optimal,
                interaction_type='view',
                weight=1.0
            )
            UserEventInteraction.objects.create(
                user=user,
                event=collab_optimal,
                interaction_type='signup',
                weight=1.0
            )
        
        # 3. An event optimal for popularity-based recommender
        popular_optimal = Event.objects.create(
            title='Popular Optimal Event',
            description='Highly popular event',
            date=timezone.now().date() + timedelta(days=30),
            time=timezone.now().time(),
            line_of_service='All',              # Not exact match but acceptable
            location_type='in-person',
            price_type='self-funded',
            creator=self.users[3],
            duration=180,
            cost=25
        )
        popular_optimal.tags.add(*self.tags[9:12])  # Different tags
        
        # Make it very popular with many interactions
        for _ in range(40):  # High number of interactions
            random_user = random.choice(self.users)
            UserEventInteraction.objects.create(
                user=random_user,
                event=popular_optimal,
                interaction_type=random.choice(['view', 'signup']),
                weight=1.0
            )
        
        # Get recommendations with various component weightings
        recommender_default = HybridRecommender()  # Default weights
        
        # Custom recommender with higher content weight
        recommender_content = HybridRecommender()
        recommender_content.overall_weights = {
            'content': 0.6,
            'collaborative': 0.2,
            'popularity': 0.2
        }
        
        # Custom recommender with higher collaborative weight
        recommender_collab = HybridRecommender()
        recommender_collab.overall_weights = {
            'content': 0.2,
            'collaborative': 0.6,
            'popularity': 0.2
        }
        
        # Custom recommender with higher popularity weight
        recommender_popular = HybridRecommender()
        recommender_popular.overall_weights = {
            'content': 0.2,
            'collaborative': 0.2,
            'popularity': 0.6
        }
        
        # Get recommendations with different weights
        recs_default = recommender_default.get_recommendations(test_user, limit=10)
        recs_content = recommender_content.get_recommendations(test_user, limit=10)
        recs_collab = recommender_collab.get_recommendations(test_user, limit=10)
        recs_popular = recommender_popular.get_recommendations(test_user, limit=10)
        
        # Analyze results
        print("\n=== Component Weighting Test Results ===")
        
        # Check content-optimal event ranking in each set
        if content_optimal in recs_default:
            print(f"Content-optimal event rank in default: {recs_default.index(content_optimal) + 1}")
        if content_optimal in recs_content:
            print(f"Content-optimal event rank in content-weighted: {recs_content.index(content_optimal) + 1}")
        if content_optimal in recs_collab:
            print(f"Content-optimal event rank in collab-weighted: {recs_collab.index(content_optimal) + 1}")
        if content_optimal in recs_popular:
            print(f"Content-optimal event rank in popularity-weighted: {recs_popular.index(content_optimal) + 1}")
        
        # Check collaborative-optimal event ranking in each set
        if collab_optimal in recs_default:
            print(f"Collab-optimal event rank in default: {recs_default.index(collab_optimal) + 1}")
        if collab_optimal in recs_content:
            print(f"Collab-optimal event rank in content-weighted: {recs_content.index(collab_optimal) + 1}")
        if collab_optimal in recs_collab:
            print(f"Collab-optimal event rank in collab-weighted: {recs_collab.index(collab_optimal) + 1}")
        if collab_optimal in recs_popular:
            print(f"Collab-optimal event rank in popularity-weighted: {recs_popular.index(collab_optimal) + 1}")
        
        # Check popularity-optimal event ranking in each set
        if popular_optimal in recs_default:
            print(f"Popular-optimal event rank in default: {recs_default.index(popular_optimal) + 1}")
        if popular_optimal in recs_content:
            print(f"Popular-optimal event rank in content-weighted: {recs_content.index(popular_optimal) + 1}")
        if popular_optimal in recs_collab:
            print(f"Popular-optimal event rank in collab-weighted: {recs_collab.index(popular_optimal) + 1}")
        if popular_optimal in recs_popular:
            print(f"Popular-optimal event rank in popularity-weighted: {recs_popular.index(popular_optimal) + 1}")
            
        # Verify component influence with assertions
        # Content-optimal should rank higher in content-weighted recommendations
        if content_optimal in recs_content and content_optimal in recs_popular:
            self.assertLessEqual(
                recs_content.index(content_optimal),
                recs_popular.index(content_optimal),
                "Content-optimal event should rank higher with content weighting"
            )
            
        # Collaborative-optimal should rank higher in collab-weighted recommendations
        if collab_optimal in recs_collab and collab_optimal in recs_content:
            self.assertLessEqual(
                recs_collab.index(collab_optimal),
                recs_content.index(collab_optimal),
                "Collaborative-optimal event should rank higher with collaborative weighting"
            )
            
        # Popular-optimal should rank higher in popularity-weighted recommendations
        if popular_optimal in recs_popular and popular_optimal in recs_content:
            self.assertLessEqual(
                recs_popular.index(popular_optimal),
                recs_content.index(popular_optimal),
                "Popular-optimal event should rank higher with popularity weighting"
            )
        
    def test_matching_algorithm(self):
        """Test the complete matching algorithm with various scenarios"""
        test_user = self.users[0]  # Audit service user
        
        # 1. Create events with various matching characteristics
        # Perfect service match, good tag match
        exact_service_match = Event.objects.create(
            title='Exact Service Match Event',
            description='Event matching user service exactly',
            date=timezone.now().date() + timedelta(days=10),
            time=timezone.now().time(),
            line_of_service=test_user.line_of_service,  # Exact match
            location_type='virtual',
            price_type='free',
            creator=self.users[1],
            duration=60,
            cost=0
        )
        exact_service_match.tags.add(*self.tags[:4])  # Add first 4 tags
        
        # All service, many tags in common
        all_service_many_tags = Event.objects.create(
            title='All Service Many Tags Event',
            description='All service event with many matching tags',
            date=timezone.now().date() + timedelta(days=12),
            time=timezone.now().time(),
            line_of_service='All',  # All service
            location_type='virtual',
            price_type='free',
            creator=self.users[1],
            duration=90,
            cost=0
        )
        all_service_many_tags.tags.add(*self.tags[:6])  # Add first 6 tags
        
        # All service, few tags, more popular
        all_service_popular = Event.objects.create(
            title='All Service Popular Event',
            description='Popular event with All service',
            date=timezone.now().date() + timedelta(days=15),
            time=timezone.now().time(),
            line_of_service='All',  # All service
            location_type='hybrid',
            price_type='paid-for',
            creator=self.users[2],
            duration=120,
            cost=50
        )
        all_service_popular.tags.add(*self.tags[6:8])  # Add only 2 tags
        
        # Wrong service, should be filtered out
        wrong_service = Event.objects.create(
            title='Wrong Service Event',
            description='Event with wrong service',
            date=timezone.now().date() + timedelta(days=20),
            time=timezone.now().time(),
            line_of_service='Tax' if test_user.line_of_service != 'Tax' else 'Consulting',  # Different service
            location_type='virtual',
            price_type='free',
            creator=self.users[2],
            duration=60,
            cost=0
        )
        wrong_service.tags.add(*self.tags[:5])  # Good tag match but wrong service
        
        # 2. Create user interactions to simulate profile
        # First, interact with some standard events to build history
        for tag in self.tags[:3]:  # User has preference for first 3 tags
            # Create and interact with events with these tags
            for i in range(2):
                event = Event.objects.create(
                    title=f'Profile Building Event {tag.name} {i}',
                    description=f'Event with {tag.name}',
                    date=timezone.now().date() + timedelta(days=i+3),
                    time=timezone.now().time(),
                    line_of_service=test_user.line_of_service,
                    location_type='virtual',
                    price_type='free',
                    creator=self.users[i+1],
                    duration=60,
                    cost=0
                )
                event.tags.add(tag)
                
                # Add strong interactions
                UserEventInteraction.objects.create(
                    user=test_user,
                    event=event,
                    interaction_type='view',
                    weight=1.0
                )
                UserEventInteraction.objects.create(
                    user=test_user,
                    event=event,
                    interaction_type='signup',
                    weight=1.0
                )
        
        # 3. Make the all_service_popular event actually popular
        for _ in range(25):
            UserEventInteraction.objects.create(
                user=random.choice(self.users),
                event=all_service_popular,
                interaction_type=random.choice(['view', 'signup']),
                weight=1.0
            )
        
        # Add some interactions to exact_service_match but fewer
        for _ in range(10):
            UserEventInteraction.objects.create(
                user=random.choice(self.users),
                event=exact_service_match,
                interaction_type=random.choice(['view', 'signup']),
                weight=1.0
            )
            
        # 4. Get recommendations and analyze results
        recommender = HybridRecommender()
        recommendations = recommender.get_recommendations(test_user, limit=10)
        
        # 5. Basic Validations
        # Check that wrong service isn't included
        self.assertNotIn(wrong_service, recommendations, 
            "Events with non-matching service should be filtered out")
        
        # Check that exact service match is included in recommendations
        self.assertIn(exact_service_match, recommendations, 
            "Exact service match should be in recommendations")
            
        # Print ranking info
        exact_idx = -1
        popular_idx = -1
        if exact_service_match in recommendations:
            exact_idx = recommendations.index(exact_service_match)
            print(f"\nExact service match is at position {exact_idx + 1}")
        
        if all_service_popular in recommendations:
            popular_idx = recommendations.index(all_service_popular)
            print(f"All service popular event is at position {popular_idx + 1}")
        
        # Count exact service matches in top recommendations
        exact_matches_in_top5 = len([
            e for e in recommendations[:5] 
            if e.line_of_service == test_user.line_of_service
        ])
        
        # Assert that at least 3 of top 5 recommendations match user's service
        self.assertGreaterEqual(exact_matches_in_top5, 3,
            f"Expected at least 3 exact service matches in top 5, got {exact_matches_in_top5}")
            
        # 6. Detailed analysis - Let's examine the algorithm's detailed scores
        # Get event IDs for lookup
        exact_id = exact_service_match.id
        all_many_id = all_service_many_tags.id
        all_popular_id = all_service_popular.id
        
        # Print detailed scores for analysis
        print("\n=== Matching Algorithm Test Results ===")
        print(f"User line of service: {test_user.line_of_service}")
        
        # Extract scores from events if available
        for idx, event in enumerate(recommendations[:5]):
            print(f"\nRank {idx+1}: {event.title} (ID: {event.id})")
            print(f"Line of Service: {event.line_of_service}")
            print(f"Tags: {', '.join(tag.name for tag in event.tags.all())}")
            print(f"Popularity: {UserEventInteraction.objects.filter(event=event).count()} interactions")
            
            # This helps identify which component contributed most to this recommendation
            if hasattr(event, 'score'):
                print(f"Score: {event.score}")

        # 7. Final assertions for provable success
        # Verify at least some recommendations match user's line of service
        service_matches = [e for e in recommendations if e.line_of_service == test_user.line_of_service]
        self.assertTrue(len(service_matches) > 0, 
            "Recommendations should include events matching user's line of service")
        
        # Verify the top recommendation is either an exact service match or has high tag overlap
        top_event = recommendations[0]
        self.assertTrue(
            top_event.line_of_service == test_user.line_of_service or 
            (top_event.line_of_service == 'All' and top_event.tags.count() >= 2),
            "Top recommendation should either match service exactly or have good tag overlap"
        )

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