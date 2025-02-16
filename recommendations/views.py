from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import HybridRecommender, CollaborativeRecommender
from main.models import Event
from .models import UserEventInteraction, EventInterest, EventSimilarity
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
import json
import logging

logger = logging.getLogger(__name__)

@login_required
@never_cache
def recommended_events(request):
    """View for displaying personalized event recommendations"""
    # Clear existing similarities to force refresh
    EventSimilarity.objects.all().delete()
    
    # Initialize our recommender
    recommender = HybridRecommender()
    
    # Compute new similarities
    recommender.content_based.compute_event_similarities()
    
    # Get fresh recommendations
    recommended = recommender.get_recommendations(request.user, limit=6)
    
    # Get similar events to ones the user has interacted with recently
    recent_interaction = UserEventInteraction.objects.filter(
        user=request.user
    ).order_by('-timestamp').first()
    
    similar_events = []
    if recent_interaction:
        content_recommender = recommender.content_based
        similar_events = content_recommender.get_similar_events(
            recent_interaction.event.id, 
            limit=3
        )
    
    context = {
        'recommended_events': recommended,
        'similar_events': similar_events,
    }
    
    return render(request, 'recommendations/recommended_events.html', context)

@login_required
def record_event_interaction(request, event_id):
    """AJAX view to record user interactions with events"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            interaction_type = data.get('interaction_type')
            event = Event.objects.get(id=event_id)
            
            # Record the interaction
            UserEventInteraction.objects.create(
                user=request.user,
                event=event,
                interaction_type=interaction_type,
                weight=5.0 if interaction_type == 'signup' else 1.0
            )
            
            # Force similarity recomputation
            recommender = ContentBasedRecommender()
            recommender.compute_event_similarities()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error recording interaction: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error'}, status=400)

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
            weight=3  # Similar weight to viewing
        )
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@never_cache
def verify_recommendations(request):
    recommender = HybridRecommender()
    recommendations = recommender.get_recommendations(request.user, limit=5)
    
    context = {
        'recommendations': recommendations,
        'user_interactions': UserEventInteraction.objects.filter(user=request.user),
        'scores': recommender.get_detailed_scores(request.user)
    }
    return render(request, 'recommendations/verify.html', context) 