from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .models import EventSimilarity
from main.models import Event, Tag
from django.db.models import Count, Q, F, ExpressionWrapper, Case, When, FloatField, Sum
from collections import defaultdict
from datetime import datetime, timedelta
from .models import UserEventInteraction
from django.utils import timezone
import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

logger = logging.getLogger(__name__)

class ContentBasedRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
    def _get_cost_range(self, cost, price_type=None):
        """Helper to categorize cost into ranges"""
        logger.debug(f"Getting cost range for cost: {cost}, price_type: {price_type}")
        
        if cost is None or price_type in ['free', 'paid-for']:
            logger.debug("Returning 'free' due to None cost or free/paid-for type")
            return "free"
        elif cost <= 25:
            logger.debug("Returning 'low' cost range")
            return "low"
        elif cost <= 50:
            logger.debug("Returning 'medium' cost range")
            return "medium"
        else:
            logger.debug("Returning 'high' cost range")
            return "high"

    def prepare_event_features(self, event):
        # If line of service is 'All', include all possible services to match with any
        line_of_service = event.line_of_service
        if line_of_service == 'All':
            line_of_service = ' '.join(['All', 'Audit', 'Consulting', 'Tax', 'Advisory', 'Assurance'])
        
        features = [
            event.title,
            event.location_type,
            line_of_service,
            ' '.join(tag.name for tag in event.tags.all()),
            event.event_type if hasattr(event, 'event_type') else '',
            f"price_{event.price_type}",
            f"cost_range_{self._get_cost_range(event.cost, event.price_type)}" if event.cost else "cost_free"
        ]
        return ' '.join(str(feature).lower() for feature in features if feature)

    def compute_event_similarities(self):
        """Compute and store similarity scores between all events"""
        # Get all active events
        events = Event.objects.prefetch_related('tags').all()
        
        if not events:
            return
        
        # Prepare text features for all events
        event_features = [self.prepare_event_features(event) for event in events]
        
        # Create TF-IDF matrix
        tfidf_matrix = self.vectorizer.fit_transform(event_features)
        
        # Compute cosine similarity
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        EventSimilarity.objects.all().delete()
        
        # Store new similarities (only store if similarity > 0.1 to save space)
        similarities_to_create = []
        for i, event1 in enumerate(events):
            for j, event2 in enumerate(events[i+1:], i+1):
                similarity = similarity_matrix[i][j]
                if similarity > 0.1:  # Only store meaningful similarities
                    similarities_to_create.append(
                        EventSimilarity(
                            event1=event1,
                            event2=event2,
                            similarity_score=float(similarity)
                        )
                    )
                    
        # Bulk create for better performance
        EventSimilarity.objects.bulk_create(similarities_to_create)

    def get_similar_events(self, event_id, limit=5):
        """Get similar events for a given event"""
        similar_events = (EventSimilarity.objects
            .filter(event1_id=event_id)
            .select_related('event2')
            .order_by('-similarity_score')[:limit])
        
        return [sim.event2 for sim in similar_events]

    def get_recommendations_for_user(self, user, limit=5):
        """Get content-based recommendations for a user based on their event history"""
        current_time = timezone.now()
        logger.info(f"\n{'='*50}\nGetting recommendations for user {user.username} (ID: {user.id})")
        
        # Get events the user has interacted with
        user_interactions = UserEventInteraction.objects.filter(
            user=user
        ).select_related('event').distinct()
        
        logger.info(f"Found {user_interactions.count()} total interactions")
        
        # If user has no interactions, return profile-based recommendations
        if not user_interactions.exists():
            logger.warning(f"No interactions found for user {user.username} - falling back to profile-based")
            return self._get_profile_based_recommendations(user, limit)
        
        # Get set of events user has already interacted with
        interacted_events = set(interaction.event for interaction in user_interactions)
        logger.info(f"User has interacted with {len(interacted_events)} unique events")
        
        # Get similar events for each event the user has interacted with
        similar_events = defaultdict(float)
        
        for interaction in user_interactions:
            event = interaction.event
            logger.info(f"\nProcessing interaction with event '{event.title}' (ID: {event.id})")
            logger.info(f"Interaction type: {interaction.interaction_type}, Weight: {interaction.weight}")
            
            # Get similarities for this event
            event_similarities = EventSimilarity.objects.filter(
                event1=event,
                # Filter out expired events
                event2__date__gte=current_time.date(),
                event2__time__gte=current_time.time() if F('date')==current_time.date() else '00:00'
            ).select_related('event2')
            
            logger.info(f"Found {event_similarities.count()} similar events")
            
            for sim in event_similarities:
                event2 = sim.event2
                logger.debug(f"\nEvaluating similar event: '{event2.title}' (ID: {event2.id})")
                logger.debug(f"Similarity score: {sim.similarity_score}")
                
                if event2.is_full():
                    logger.debug("Skipping - Event is full")
                    continue
                    
                if event2 in interacted_events:
                    logger.debug("Skipping - User already interacted with this event")
                    continue
                
                score = sim.similarity_score * interaction.weight
                similar_events[event2] += score
                logger.debug(f"Added score {score} (Total: {similar_events[event2]})")
        
        # Sort and log recommendations
        recommended_events = sorted(
            similar_events.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        logger.info("\nFinal Recommendations:")
        for event, score in recommended_events[:limit]:
            logger.info(f"- {event.title} (ID: {event.id})")
            logger.info(f"  Score: {score}")
            logger.info(f"  Tags: {', '.join(tag.name for tag in event.tags.all())}")
            logger.info(f"  Service: {event.line_of_service}")
            logger.info(f"  Location: {event.location_type}")
        
        final_recommendations = [event for event, _ in recommended_events[:limit]]
        logger.info(f"\nReturning {len(final_recommendations)} recommendations")
        
        return final_recommendations

    def _get_profile_based_recommendations(self, user, limit=5):
        """Get recommendations based on user profile when no interactions exist"""
        current_time = timezone.now()
        
        # Build query based on user preferences
        query = Event.objects.filter(
            date__gte=current_time.date(),
            time__gte=current_time.time() if F('date')==current_time.date() else '00:00'
        )
        
        if user.line_of_service != 'All':
            # Try to get exact matches first
            exact_matches = query.filter(line_of_service=user.line_of_service)
            if exact_matches.exists():
                query = exact_matches
            else:
                # Only include 'All' events if no exact matches exist
                query = query.filter(line_of_service='All')
        
        # Then add scoring
        query = query.annotate(
            match_score=ExpressionWrapper(
                Case(
                    When(line_of_service=user.line_of_service, then=10.0),
                    When(line_of_service='All', then=3.0),
                    default=0.0,
                    output_field=FloatField(),
                ) +
                Case(  # Additional weights for accessibility
                    When(price_type='free', then=2.0),
                    When(price_type='self-funded', then=1.0),
                    default=0.0,
                    output_field=FloatField(),
                ) +
                Case(  # Duration preference
                    When(duration__lte=120, then=1.0),
                    default=0.0,
                    output_field=FloatField(),
                ),
                output_field=FloatField()
            )
        ).order_by('-match_score', '-date')
        
        logger.debug(f"\nGetting profile-based recommendations for user {user.id}")
        logger.debug(f"User line of service: {user.line_of_service}")
        
        recommendations = list(query[:limit])
        logger.debug(f"Found {len(recommendations)} profile-based recommendations")
        for event in recommendations:
            logger.debug(f"Recommending {event.title} (score: {event.match_score:.2f}, service: {event.line_of_service})")
        
        return recommendations

class CollaborativeRecommender:
    def __init__(self):
        self.min_interactions = 3  
    def _create_user_event_matrix(self):
        """Create a user-event interaction matrix"""
        # Get all interactions
        interactions = UserEventInteraction.objects.select_related('user', 'event').all()
        
        # Create user and event indices
        users = list(set(inter.user_id for inter in interactions))
        events = list(set(inter.event_id for inter in interactions))
        user_indices = {user_id: i for i, user_id in enumerate(users)}
        event_indices = {event_id: i for i, event_id in enumerate(events)}
        
        # Create interaction matrix
        matrix = np.zeros((len(users), len(events)))
        
        # Fill matrix with weighted interactions
        for interaction in interactions:
            user_idx = user_indices[interaction.user_id]
            event_idx = event_indices[interaction.event_id]
            matrix[user_idx, event_idx] = interaction.weight
            
        return matrix, users, events, user_indices, event_indices
    
    def get_similar_users(self, user_id, limit=5):
        """Find users with similar event preferences"""
        matrix, users, events, user_indices, event_indices = self._create_user_event_matrix()
        
        if user_id not in user_indices:
            return []
            
        user_idx = user_indices[user_id]
        user_vector = matrix[user_idx].reshape(1, -1)
        
        # Calculate similarity with all other users
        similarities = cosine_similarity(user_vector, matrix)[0]
        
        # Get most similar users (excluding self)
        similar_indices = np.argsort(similarities)[::-1][1:limit+1]
        return [users[idx] for idx in similar_indices]
    
    def get_recommendations_for_user(self, user, limit=5):
        """Get collaborative filtering recommendations for a user"""
        # Get user's past interactions
        user_interactions = UserEventInteraction.objects.filter(user=user)
        
        if user_interactions.count() < self.min_interactions:
            return []  # Not enough interactions for reliable recommendations
            
        # Get similar users
        similar_users = self.get_similar_users(user.id)
        
        if not similar_users:
            return []
            
        # Get events that similar users have interacted with
        current_time = timezone.now()
        query = Event.objects.filter(
            usereventinteraction__user_id__in=similar_users,
            # Filter out expired events
            date__gte=current_time.date(),
            # For today's events, only show future ones
            time__gte=current_time.time() if F('date')==current_time.date() else '00:00'
        ).exclude(
            usereventinteraction__user=user
        )
        
        # Filter by line of service
        if user.line_of_service != 'All':
            query = query.filter(
                Q(line_of_service=user.line_of_service) | 
                Q(line_of_service='All')
            )
        
        similar_user_events = query.annotate(
            interaction_count=Count('usereventinteraction')
        ).order_by('-interaction_count')[:limit]
        
        return list(similar_user_events)
    
    def record_interaction(self, user, event, interaction_type, weight=None):
        """Record a user's interaction with an event"""
        if weight is None:
            # Define default weights for different interaction types
            weights = {
                'view': 2,
                'signup': 8,
                'rate': 5,
            }
            weight = weights.get(interaction_type, 1)
            
        # Update or create interaction
        interaction, created = UserEventInteraction.objects.update_or_create(
            user=user,
            event=event,
            interaction_type=interaction_type,
            defaults={'weight': weight}
        )
        return interaction 

class HybridRecommender:
    def __init__(self):
        self.content_based = ContentBasedRecommender()
        self.collaborative = CollaborativeRecommender()
        
        # Distributed weights of individual event components
        self.content_weights = {
            'title_similarity': 0.20,     
            'tags_match': 0.20,           
            'price_match': 0.20,         
            'location_type_match': 0.15,  
            'line_of_service_match': 0.15,
            'event_type_match': 0.10      
        }
        
        # Keep overall weights the same
        self.overall_weights = {
            'content': 0.5,      
            'collaborative': 0.4, 
            'popularity': 0.1  
        }
        
        # Verify overall weights sum to 1.0
        overall_sum = sum(self.overall_weights.values())
        logger.debug(f"Overall weights sum: {overall_sum}")
        if not 0.99 <= overall_sum <= 1.01:
            logger.error(f"Overall weights don't sum to 1.0! Current sum: {overall_sum}")

    def _get_popular_events(self, limit=5, user=None):
        """Get popular events based on interaction count and features"""
        current_time = timezone.now()
        query = Event.objects.filter(
            # Only upcoming events
            date__gte=current_time.date(),
            # For today's events, only show future ones
            time__gte=current_time.time() if F('date')==current_time.date() else '00:00'
        )
        
        # Filter by line of service if a user is provided
        if user and user.line_of_service != 'All':
            query = query.filter(
                Q(line_of_service=user.line_of_service) | 
                Q(line_of_service='All')
            )
        
        # Get weighted interaction count - includes the weight of interactions
        query = query.annotate(
            interaction_count=Count('usereventinteraction'),
            weighted_interaction=Sum('usereventinteraction__weight'),
            # Add weights for different features
            weighted_score=ExpressionWrapper(
                (F('weighted_interaction') * 1.0) + F('interaction_count') * 0.2 +
                Case(
                    # Significantly increase the weight for exact service match
                    When(line_of_service=user.line_of_service if user else None, then=20.0),
                    # All service is good but not as good as exact match
                    When(line_of_service='All', then=2.0),
                    default=0.0,
                    output_field=FloatField(),
                ) +
                Case(
                    When(price_type='free', then=2.0),
                    When(price_type='self-funded', then=1.0),
                    default=0.0,
                ) +
                Case(
                    When(duration__lte=60, then=1.5),  # Favor shorter events even more
                    When(duration__lte=120, then=1.0),
                    default=0.0,
                ),
                output_field=FloatField()
            )
        ).order_by('-weighted_score')[:limit]
        
        return query

    def get_recommendations(self, user, limit=5):
        """Get hybrid recommendations considering all event features"""
        logger.debug(f"Getting recommendations for user {user.id}, limit {limit}")
        
        # Handle invalid limit
        if limit <= 0:
            return []
        
        # Get recommendations from each source
        content_recs = self.content_based.get_recommendations_for_user(user, limit=limit)
        logger.debug(f"Content-based recommendations: {[e.id for e in content_recs]}")
        
        collaborative_recs = self.collaborative.get_recommendations_for_user(user, limit=limit)
        logger.debug(f"Collaborative recommendations: {[e.id for e in collaborative_recs]}")
        
        popular_recs = self._get_popular_events(limit=limit, user=user)
        logger.debug(f"Popular recommendations: {[e.id for e in popular_recs]}")
        
        event_scores = {}
        
        # Add content-based recommendations with feature weights
        for i, event in enumerate(content_recs):
            base_score = (limit - i) / limit
            content_base = base_score * self.overall_weights['content']
            logger.debug(f"\nScoring content-based event {event.id}:")
            logger.debug(f"Base score: {base_score}")
            logger.debug(f"Content base score: {content_base}")
            
            # Initialize event score with title similarity
            event_scores[event] = self.content_weights['title_similarity'] * content_base
            logger.debug(f"Initial title similarity score: {event_scores[event]}")
            
            # Add price preference weight
            if hasattr(user, 'preferred_price_type') and event.price_type == user.preferred_price_type:
                price_score = self.content_weights['price_match'] * content_base
                event_scores[event] += price_score
                logger.debug(f"Added price match score: {price_score}")
            
            # Add location type preference weight
            if hasattr(user, 'preferred_location_type') and event.location_type == user.preferred_location_type:
                location_score = self.content_weights['location_type_match'] * content_base
                event_scores[event] += location_score
                logger.debug(f"Added location type match score: {location_score}")
            
            # Add line of service match score
            if (event.line_of_service == 'All' or  # Event is for all services
                user.line_of_service == event.line_of_service or  # Exact match
                event.line_of_service in user.line_of_service.split(',')):  # Handle multiple services
                service_score = self.content_weights['line_of_service_match'] * content_base
                event_scores[event] += service_score
                logger.debug(f"Added line of service match score: {service_score}")
                logger.debug(f"Event service: {event.line_of_service}, User service: {user.line_of_service}")
            else:
                logger.debug(f"No service match - Event: {event.line_of_service}, User: {user.line_of_service}")
            
            logger.debug(f"Final content score for event {event.id}: {event_scores[event]}")
        
        # Add collaborative recommendations
        for i, event in enumerate(collaborative_recs):
            score = self.overall_weights['collaborative'] * (limit - i) / limit
            previous_score = event_scores.get(event, 0)
            event_scores[event] = previous_score + score
            logger.debug(f"\nCollaborative event {event.id}:")
            logger.debug(f"Score contribution: {score}")
            logger.debug(f"Previous score: {previous_score}")
            logger.debug(f"New total score: {event_scores[event]}")
        
        # Add popularity recommendations
        for i, event in enumerate(popular_recs):
            score = self.overall_weights['popularity'] * (limit - i) / limit
            previous_score = event_scores.get(event, 0)
            event_scores[event] = previous_score + score
            logger.debug(f"\nPopularity event {event.id}:")
            logger.debug(f"Score contribution: {score}")
            logger.debug(f"Previous score: {previous_score}")
            logger.debug(f"New total score: {event_scores[event]}")
        
        # Sort and log final scores
        sorted_events = sorted(
            event_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        logger.debug("\nFinal event scores:")
        for event, score in sorted_events:
            logger.debug(f"Event {event.id}: {score}")
        
        final_recommendations = [event for event, score in sorted_events[:limit]]
        logger.debug(f"Final recommendations: {[e.id for e in final_recommendations]}")
        
        return final_recommendations 

    def get_detailed_scores(self, user):
        """Get detailed scoring breakdown for verification"""
        scores = {
            'content_based': {},
            'collaborative': {},
            'popularity': {}
        }
        
        # Get all scores (reuse existing logging)
        content_recs = self.content_based.get_recommendations_for_user(user)
        collaborative_recs = self.collaborative.get_recommendations_for_user(user)
        popular_recs = self._get_popular_events()
        
        # Store scores with breakdowns
        for event in content_recs:
            scores['content_based'][event.id] = {
                'title': event.title,
                'tags_match': self.content_weights['tags_match'],
                'location_match': self.content_weights['location_type_match'],
                'line_of_service': self.content_weights['line_of_service_match'],
                'total_score': self.overall_weights['content']
            }
            
        return scores




