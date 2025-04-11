from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import HybridRecommender, CollaborativeRecommender
from main.models import Event
from .models import UserEventInteraction, EventInterest, EventSimilarity
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
import json
import logging
from datetime import date

logger = logging.getLogger(__name__)

@login_required
@never_cache
def recommended_events(request):
    """View for displaying personalized event recommendations"""
    try:
        # Clear existing similarities to force refresh
        EventSimilarity.objects.all().delete()
        
        # Initialize our recommender
        recommender = HybridRecommender()
        
        # Compute new similarities and get recommendations
        recommender.content_based.compute_event_similarities()
        recommended = recommender.get_recommendations(request.user, limit=9)
        
        # Get similar events based on recent interaction
        recent_interaction = UserEventInteraction.objects.filter(
            user=request.user
        ).order_by('-timestamp').first()
        
        similar_events = []
        if recent_interaction:
            similar_events = recommender.content_based.get_similar_events(
                recent_interaction.event.id, 
                limit=3
            )
        
        # Add today's date for past event detection
        today = date.today()
        
        context = {
            'recommended_events': recommended,
            'similar_events': similar_events,
            'today': today,
        }
        
        logger.info(f"Generated recommendations for user {request.user.username}")
        return render(request, 'recommendations/recommended_events.html', context)
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        return render(request, 'recommendations/error.html', {'error': str(e)})

@login_required
def record_event_interaction(request, event_id):
    """AJAX view to record user interactions with events"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            interaction_type = data.get('interaction_type')
            event = Event.objects.get(id=event_id)
            
            # Record the interaction
            interaction = UserEventInteraction.objects.create(
                user=request.user,
                event=event,
                interaction_type=interaction_type,
                weight=5.0 if interaction_type == 'signup' else 1.0
            )
            
            # Force recommendation refresh using HybridRecommender
            recommender = HybridRecommender()
            recommender.content_based.compute_event_similarities()
            
            logger.info(f"Recorded {interaction_type} interaction for user {request.user.username} on event {event_id}")
            return JsonResponse({'status': 'success'})
            
        except Event.DoesNotExist:
            logger.error(f"Event {event_id} not found")
            return JsonResponse({'status': 'error', 'message': 'Event not found'}, status=404)
        except Exception as e:
            logger.error(f"Error recording interaction: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def record_event_interest(request, event_id):
    if request.method == 'POST':
        event = Event.objects.get(id=event_id)
        
        # Record interest
        EventInterest.objects.get_or_create(
            user=request.user,
            event=event
        )
        
        # Record this as an interaction for recommendations
        recommender = CollaborativeRecommender()
        recommender.record_interaction(
            user=request.user,
            event=event,
            interaction_type='interest',
            weight=6  # Similar weight to viewing
        )
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@never_cache
def verify_recommendations(request):
    """Debug view to verify recommendation system behavior"""
    try:
        # Get recent interactions for the current user
        recent_interactions = UserEventInteraction.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:10]  # Limit to last 10 interactions for clarity
        
        # Get current recommendations and force a fresh calculation
        recommender = HybridRecommender()
        # Force recalculation of similarities
        recommender.content_based.compute_event_similarities()
        recommendations = recommender.get_recommendations(request.user, limit=10)
        
        # Get detailed scores for debugging
        scores = recommender.get_debug_scores(request.user)
        
        context = {
            'user_interactions': recent_interactions,  # Use the filtered recent interactions
            'recommendations': recommendations,
            'scores': scores,
            'total_interactions': UserEventInteraction.objects.filter(user=request.user).count(),
            'interaction_types': UserEventInteraction.objects.filter(user=request.user).values_list('interaction_type', flat=True).distinct()
        }
        
        logger.info(f"Generated verification data for user {request.user.username}")
        return render(request, 'recommendations/verify.html', context)
        
    except Exception as e:
        logger.error(f"Error in verification view: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Error generating verification data',
            'detail': str(e)
        }, status=500)

@login_required
def debug_similarities(request, event_id):
    """Debug view to check similarity calculations for a specific event"""
    try:
        event = Event.objects.get(id=event_id)
        recommender = HybridRecommender()
        
        # Force recalculation
        recommender.content_based.compute_event_similarities()
        
        # Get all similarities for this event
        similarities = EventSimilarity.objects.filter(
            event1=event
        ).select_related('event2').order_by('-similarity_score')
        
        context = {
            'event': event,
            'similarities': [
                {
                    'event': sim.event2,
                    'score': sim.similarity_score,
                    'matching_tags': set(event.tags.all()) & set(sim.event2.tags.all()),
                    'service_match': event.line_of_service == sim.event2.line_of_service,
                    'location_match': event.location_type == sim.event2.location_type
                }
                for sim in similarities[:10]  # Show top 10
            ]
        }
        
        return render(request, 'recommendations/debug_similarities.html', context)
        
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)

