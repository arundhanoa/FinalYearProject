from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Event

@login_required
def my_events(request):
    today = timezone.now().date()
    user = request.user
    
    print(f"\nCurrent user accessing my_events: {user.username}")
    
    # Get events created by this user
    created_events = Event.objects.filter(creator=user)
    
    # Get events where user is registered through EventSignUp
    # Modified this query to ensure it captures all registered events
    signed_up_events = Event.objects.filter(
        eventsignup__user=user,
        eventsignup__status='registered'  # Add this if you have a status field
    ).distinct()
    
    print(f"User ID: {user.id}")
    print(f"Created events count: {created_events.count()}")
    print(f"Created events: {[e.title for e in created_events]}")
    print(f"Signed up events count: {signed_up_events.count()}")
    print(f"Signed up events: {[e.title for e in signed_up_events]}")
    
    # Split into past and upcoming
    created_past = created_events.filter(date__lt=today).order_by('-date')
    created_upcoming = created_events.filter(date__gte=today).order_by('date')
    signed_up_past = signed_up_events.filter(date__lt=today).order_by('-date')
    signed_up_upcoming = signed_up_events.filter(date__gte=today).order_by('date')
    
    context = {
        'created_past': created_past,
        'created_upcoming': created_upcoming,
        'signed_up_past': signed_up_past,
        'signed_up_upcoming': signed_up_upcoming,
    }
    
    return render(request, 'main/my_events.html', context) 