from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Tag, EventImage, EventSignUp, Announcement
from recommendations.models import UserEventInteraction
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from .forms import CustomUserCreationForm
from django.db import transaction
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import rotate_token
from .models import CustomUser
from django.views.decorators.cache import never_cache
from django.db import IntegrityError
from django.db.models import Count
# Create your views here.
from loginsights.main import LogInsightsLogger
from django.db import models
from django.db.models import Q

logger = LogInsightsLogger.get_logger()

@never_cache
def all_events(request):
    # Get the show parameter from the URL
    show = request.GET.get('show', 'current')
    
    # Get current datetime
    now = timezone.now()
    
    # Base queryset
    events = Event.objects.all()
    
    # Filter based on expired status
    if show == 'expired':
        events = events.filter(date__lt=now.date())
        show_expired = True
    else:
        events = events.filter(date__gte=now.date())
        show_expired = False

    # Get filter parameters
    sort_by = request.GET.get('sort_by', '-date')
    # Validate sort_by parameter
    valid_sort_fields = ['date', 'title', 'location', '-date', '-title', '-location']
    if sort_by not in valid_sort_fields:
        sort_by = '-date'  # Default to date if invalid sort field
        
    sort_direction = request.GET.get('direction', 'desc')
    title_filter = request.GET.get('title', '')
    date_filter = request.GET.get('date', '')
    time_start = request.GET.get('time_start', '')
    time_end = request.GET.get('time_end', '')
    location_type_filter = request.GET.get('location_type', '')
    price_type_filter = request.GET.get('price_type', '')
    tag_filter = request.GET.get('tag', '')

    # Apply filters
    if title_filter:
        events = events.filter(title__icontains=title_filter)
    if date_filter:
        events = events.filter(date=date_filter)
    if time_start and time_end:
        events = events.filter(time__gte=time_start, time__lte=time_end)
    elif time_start:
        events = events.filter(time__gte=time_start)
    elif time_end:
        events = events.filter(time__lte=time_end)
    if location_type_filter:
        events = events.filter(location_type=location_type_filter)
    if price_type_filter:
        events = events.filter(price_type=price_type_filter)
    if tag_filter:
        events = events.filter(tags__name=tag_filter)

    # Apply sorting
    if sort_direction == 'asc':
        events = events.order_by(sort_by.replace('-', ''))
    else:
        events = events.order_by(f"-{sort_by.replace('-', '')}")

    # Now separate into upcoming and past
    upcoming_events = []
    past_events = []
    
    for event in events:
        event_datetime = timezone.make_aware(
            datetime.combine(event.date, event.time)
        )
        if event_datetime >= now:
            upcoming_events.append(event)
        else:
            past_events.append(event)

    # Get tags that are only used by the currently filtered events
    used_tags = Tag.objects.filter(
        event__in=events
    ).annotate(
        event_count=Count('event')
    ).filter(event_count__gt=0).distinct().order_by('name')

    context = {
        'events': events,
        'show_expired': show_expired,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'tags': used_tags,  # Replace all_tags with used_tags
        'current_filters': {
            'sort_by': sort_by,
            'direction': sort_direction,
            'title': title_filter,
            'date': date_filter,
            'time_start': time_start,
            'time_end': time_end,
            'location_type': location_type_filter,
            'price_type': price_type_filter,
            'tag': tag_filter,
        },
        'user_created_count': Event.objects.filter(creator=request.user).count() if request.user.is_authenticated else 0,
        'user_signed_up_count': Event.objects.filter(attendees=request.user).count() if request.user.is_authenticated else 0,
    }
        
    return render(request, 'main/all_events.html', context) 

@login_required
@never_cache
def all_signed_up_past(request):
    user = request.user
    now = timezone.now()
    
    # Get all past events user has signed up for
    past_events = Event.objects.filter(
        eventsignup__user=user,
        date__lt=now
    ).order_by('-date')
    
    context = {
        'events': past_events,
        'section_title': 'All Past Events I\'ve Signed Up For'
    }
    
    return render(request, 'main/event_list.html', context)

@login_required
@never_cache
def all_signed_up_upcoming(request):
    user = request.user
    now = timezone.now()
    
    # Get all upcoming events user has signed up for
    upcoming_events = Event.objects.filter(
        eventsignup__user=user,
        date__gte=now
    ).order_by('date')
    
    context = {
        'events': upcoming_events,
        'section_title': 'All Current and Upcoming Events I\'ve Signed Up For'
    }
    
    return render(request, 'main/event_list.html', context)

@login_required
@never_cache
def all_created_past(request):
    user = request.user
    now = timezone.now()
    
    # Get all past events created by user
    past_events = Event.objects.filter(
        creator=user,
        date__lt=now
    ).order_by('-date')
    
    context = {
        'events': past_events,
        'section_title': 'All Past Events I\'ve Created'
    }
    
    return render(request, 'main/event_list.html', context)

@login_required
@never_cache
def all_created_upcoming(request):
    user = request.user
    now = timezone.now()
    
    # Get all upcoming events created by user
    upcoming_events = Event.objects.filter(
        creator=user,
        date__gte=now
    ).order_by('date')
    
    context = {
        'events': upcoming_events,
        'section_title': 'All Current and Upcoming Events I\'ve Created'
    }
    
    return render(request, 'main/event_list.html', context)

@login_required
def homepage(request):
    # Get the user directly since we don't have a profile relationship
    user = request.user
    
    context = {
        'user': user,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'other_names': user.other_names,
        'work_email': user.work_email,
        'workday_id': user.workday_id,
        'line_of_service': user.line_of_service,
        'team': user.team,
        'job_title': user.job_title,
        'line_manager': user.line_manager,
        'career_coach': user.career_coach,
        'home_office': user.home_office,
        'phone_number': user.phone_number,
    }

        # Log an informational message
    logger.info(f"loading {user.first_name} on the homepage")
    
    return render(request, 'main/homepage.html', context)

@cache_page(60 * 15)
def landing(request):
    return render(request, 'main/landing.html')

def about(request):
    return render(request, 'main/about.html')

@ensure_csrf_cookie
@csrf_protect
@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('homepage')
    
    # Ensure CSRF cookie is set
    if not request.COOKIES.get('csrftoken'):
        rotate_token(request)
        
    if request.method == 'POST':
        first_name = request.POST.get('username')
        password = request.POST.get('password')
        
        if first_name and password:
            try:
                user = authenticate(request, username=first_name, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('homepage')
                else:
                    messages.error(request, 'Invalid credentials.')
            except Exception as e:
                messages.error(request, 'An error occurred. Please try again.')
        else:
            messages.error(request, 'Please enter both first name and password.')

    response = render(request, 'registration/login.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
      

@login_required
def event_view(request, event_id):
    event = get_object_or_404(
        Event.objects.prefetch_related('event_images').select_related('creator'),
        id=event_id
    )
    
    # Get all attendees through EventSignUp with a single query
    attendees = CustomUser.objects.filter(
        event_signups__event=event
    ).distinct().order_by('username')
    
    is_registered = EventSignUp.objects.filter(
        user=request.user,
        event=event
    ).exists()
    
    print(f"\nEvent View Debug:")
    print(f"User: {request.user.username}")
    print(f"Event: {event.title}")
    print(f"All attendees: {[a.username for a in attendees]}")
    print(f"Is registered: {is_registered}")
    print(f"EventSignUp exists: {is_registered}")
    print(f"Total attendee count: {attendees.count()}")

    event_view_metadata= {
        "user": request.user.username,
        "event_title": event.title,
        "attendee_count": attendees.count(),
        "is_registered": is_registered
    }
    logger.add_metric("Event View",event_view_metadata)
    
    # Get both general and personal announcements
    announcements = Announcement.objects.filter(
        Q(event=event, for_user__isnull=True) |  # General announcements
        Q(event=event, for_user=request.user)     # Personal announcements
    ).order_by('-created_at')
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'attendee_count': attendees.count(),
        'current_user': request.user,
        'attendees': attendees,
        'announcements': announcements,
    }

    logger.add_metric("Event Views", {
        "event_id": event.id,
        "event_title": event.title
    })
    
    # Force cache refresh
    response = render(request, 'main/event_view.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required
@never_cache
def my_events(request):
    today = timezone.now().date()
    user = request.user

    logger.info(f"My Events page accessed by user {user.username} with user id {user.id}")
    
    print("\n=== DEBUG INFO ===")
    print(f"Current user: {user.username} (ID: {user.id})")
    
    # Get events created by this user
    created_events = Event.objects.filter(creator=user)
    
    # Get events user has signed up for
    events_from_signups = Event.objects.filter(
        eventsignup__user=user
    ).exclude(  # Exclude events user created
        creator=user
    ).distinct()
    
    print("\n=== Registration Details ===")
    print(f"Events signed up for: {events_from_signups.count()}")
    print(f"Events created: {created_events.count()}")

    user_stats = {
        "user_id": user.id,
        "username": user.username,
        "created_events": created_events.count(),
        "signed_up_events": events_from_signups.count(),
    }
    logger.add_metric("User event statistics", user_stats)
    
    # List all registrations
    print("\nDetailed Registration Info:")
    print("From EventSignUp:")
    for event in events_from_signups:
        print(f"- {event.title} (ID: {event.id})")
    
    # Split into past and upcoming
    created_past = created_events.filter(date__lt=today).order_by('-date')
    created_upcoming = created_events.filter(date__gte=today).order_by('date')
    signed_up_past = events_from_signups.filter(date__lt=today).order_by('-date')
    signed_up_upcoming = events_from_signups.filter(date__gte=today).order_by('date')
    
    # Get announcements for events user is signed up for
    relevant_announcements = Announcement.objects.filter(
        event__in=events_from_signups,
        created_at__gt=models.Subquery(
            EventSignUp.objects.filter(
                user=request.user,
                event=models.OuterRef('event')
            ).values('signup_date')
        )
    ).select_related('event', 'created_by').order_by('-created_at')[:10]

    context = {
        'created_past': created_past,
        'created_upcoming': created_upcoming,
        'signed_up_past': signed_up_past,
        'signed_up_upcoming': signed_up_upcoming,
        'relevant_announcements': relevant_announcements,
    }
    
    # Add cache control headers
    response = render(request, 'main/my_events.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def networking(request):
    return render(request, 'main/networking.html')

def profile(request):
    return render(request, 'main/profile.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            logger.add_metric("New Users", {"Form data": form.data})
            return redirect('login')
    return render(request, 'main/register.html', {'form': form})

def settings(request):
    return render(request, 'main/settings.html')

@login_required  # Ensure the user is logged in to access settings
def settings_update(request):
    if request.method == 'POST':
        # Handle form submission and update settings
        # For example, update user profile or settings here
        # ...
        return redirect('settings')  # Redirect to the settings page or any other page after update
    return render(request, 'main/settings.html')  # Render the settings page

def teambuilding(request):
    return render(request, 'main/teambuilding.html')

def volunteering(request):
    return render(request, 'main/volunteering.html')

def help_view(request):
    return render(request, 'main/help.html')

def home(request):
    events = Event.objects.all().order_by('date')  # orders by date, adjust as needed
    return render(request, 'main/home.html', {'events': events})

@login_required
@never_cache
def event_create(request):
    if request.method == 'POST':
        print("\nEvent Create Debug:")
        print("Full POST data:", dict(request.POST))
        print(f"location_type in POST: {request.POST.get('location_type')}")
        print(f"location in POST: {request.POST.get('location')}")
        print(f"meeting_link in POST: {request.POST.get('meeting_link')}")
        
        duration = int(request.POST.get('duration', 0))
        
        event = Event(
            title=request.POST['title'],
            description=request.POST['description'],
            date=request.POST['date'],
            time=request.POST['time'],
            location=request.POST['location'],
            location_type=request.POST['location_type'],
            price_type=request.POST.get('price_type', 'free'),  # Added default
            creator=request.user,
            capacity=request.POST.get('capacity'),
            line_of_service=request.POST.get('line_of_service'),
            event_type=request.POST.get('event_types'),
            duration=request.POST.get('duration')
           
        )
        
        # Handle event types
        event_types = request.POST.getlist('event_type')  # Get all selected event types
        if event_types:
            event.event_type = ', '.join(event_types)  # Combine multiple selections
        
        
        print("\nEvent Object Debug (before save):")
        print(f"event.location_type: {event.location_type}")
        print(f"event.location: {event.location}")
        print(f"event.meeting_link: {event.meeting_link}")
        
        # Handle cost for paid/self-funded events
        cost_value = request.POST.get('cost')
        if cost_value and event.price_type in ['paid-for', 'self-funded']:
            try:
                event.cost = float(cost_value)
            except ValueError:
                print("Invalid cost value:", cost_value)
        
        # Handle meeting link for virtual/hybrid events
        if event.location_type in ['virtual', 'hybrid']:
            meeting_link = request.POST.get('meeting_link', '')
            # Make sure the link starts with http:// or https://
            if meeting_link and not meeting_link.startswith(('http://', 'https://')):
                meeting_link = 'https://' + meeting_link
            event.meeting_link = meeting_link
            print("Saved meeting link:", event.meeting_link)  # Debug print
            print("About to save event with:")
            print("- Price type:", event.price_type)
            print("- Cost:", event.cost)
            print("- Event type:", event.event_type)
        
        event.save()
        
        print("\nEvent Object Debug (after save):")
        print(f"event.id: {event.id}")
        print(f"event.location_type: {event.location_type}")
        print(f"event.location: {event.location}")
        print(f"event.meeting_link: {event.meeting_link}")

        # Save tags
        tags = request.POST.getlist('tags[]')
        for tag_name in tags:
            tag, created = Tag.objects.get_or_create(name=tag_name.strip())
            event.tags.add(tag)

        # Handle images
        if 'images' in request.FILES:
            images = request.FILES.getlist('images')
            for image in images:
                EventImage.objects.create(event=event, image=image)

        # After saving the event and handling tags
        clean_unused_tags()
        
        messages.success(request, 'Event created successfully!')
        return redirect('all_events')
        
    # Get only tags that are actually used in events
    existing_tags = Tag.objects.annotate(
        event_count=Count('event')
    ).filter(event_count__gt=0)
    
    context = {
        'existing_tags': existing_tags,
        'location_choices': Event.LOCATION_CHOICES,
        'price_choices': Event.PRICE_CHOICES,
    }
    return render(request, 'main/event_create.html', context)

@login_required
@ensure_csrf_cookie
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    is_registered = event.attendees.filter(id=request.user.id).exists()
    
    context = {
        'event': event,
        'is_registered': is_registered,
    }
    
    return render(request, 'main/event_view.html', context)

@never_cache
@csrf_protect
def logout_view(request):
    if request.user.is_authenticated:
        # Clear session and rotate CSRF token before logout
        request.session.flush()
        rotate_token(request)
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
    
    response = redirect('landing')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

def get_tags(request):
    query = request.GET.get('a', '')
    tags = Tag.objects.annotate(
        event_count=Count('event')
    ).filter(
        event_count__gt=0,
        name__icontains=query
    ).values_list('name', flat=True)
    return JsonResponse(list(tags), safe=False)

@login_required
@csrf_protect
@never_cache
def event_signup(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user = request.user
    
    if request.method == 'POST':
        try:
            signup = EventSignUp.objects.filter(user=user, event=event).first()
            print(f"\n=== EVENT SIGNUP DEBUG ===")
            print(f"Event: {event.title} (ID: {event_id})")
            print(f"User: {user.username} (ID: {user.id})")
            print(f"Current signup status: {'Registered' if signup else 'Not registered'}")
            
            if request.POST.get('unregister') and signup:
                with transaction.atomic():
                    # Handle unregistration - delete all records
                    signup.delete()
                    event.attendees.remove(user)
                    UserEventInteraction.objects.filter(
                        user=user,
                        event=event,
                        interaction_type='signup'
                    ).delete()
                    event.save()
                
                print("Action: Unregistered")
                print("- Deleted EventSignUp record")
                print("- Removed from attendees")
                print("- Removed interaction record")
                
                messages.success(request, 'Successfully unregistered from the event.')
                return redirect('myevents')
            
            elif not signup:
                with transaction.atomic():
                    # Create all necessary records atomically
                    EventSignUp.objects.create(
                        user=user,
                        event=event,
                        signup_date=timezone.now()
                    )
                    event.attendees.add(user)
                    UserEventInteraction.objects.create(
                        user=user,
                        event=event,
                        interaction_type='signup',
                        weight=5.0
                    )
                    event.save()
                
                print("Action: Registered")
                print("- Created EventSignUp record")
                print("- Added to attendees")
                print("- Created interaction record")
                
                messages.success(request, 'Successfully registered for the event!')
            
            # Verify registration status
            final_signup = EventSignUp.objects.filter(user=user, event=event).exists()
            final_attendee = event.attendees.filter(id=user.id).exists()
            final_interaction = UserEventInteraction.objects.filter(
                user=user,
                event=event,
                interaction_type='signup'
            ).exists()
            
            print(f"\nFinal Status:")
            print(f"- EventSignUp record exists: {final_signup}")
            print(f"- In attendees list: {final_attendee}")
            print(f"- Interaction record exists: {final_interaction}")
            print("=== END DEBUG ===\n")
            
        except Exception as e:
            logger.error(f"Error in event_signup {repr(e)}")
            print(f"Error in event_signup: {str(e)}")
            messages.error(request, f'An error occurred: {str(e)}')
            
    response = redirect('event_view', event_id=event_id)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) 
        if form.is_valid():
            user = form.save()
            # Redirect to a new page to display the username
            return redirect('display_username', username=user.username)
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def display_username(request, username):
    return render(request, 'registration/display_username.html', {'username': username})

@login_required
def debug_registrations(request):
    user = request.user
    signups = EventSignUp.objects.filter(user=user)
    attending = Event.objects.filter(attendees=user)
    
    context = {
        'username': user.username,
        'user_id': user.id,
        'signups': [
            {
                'event_id': s.event.id,
                'event_title': s.event.title,
                'signup_date': s.signup_date
            } for s in signups
        ],
        'attending': [
            {
                'event_id': e.id,
                'event_title': e.title
            } for e in attending
        ]
    }
    
    return JsonResponse(context)

@login_required
@never_cache
@csrf_protect
@ensure_csrf_cookie
def event_edit(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    print(f"\nEvent Edit Debug:")
    print(f"Initial event location_type: {event.location_type}")
    
    if event.creator != request.user:
        messages.error(request, "You don't have permission to edit this event.")
        return redirect('event_view', event_id=event_id)
    
    duration_hours = event.duration // 60 if event.duration else 0
    duration_minutes = event.duration % 60 if event.duration else 0
        
    if request.method == 'POST':
        print("\nPOST Data Debug:")
        print(f"location_type in POST: {request.POST.get('location_type')}")
        print(f"location in POST: {request.POST.get('location')}")
        print(f"meeting_link in POST: {request.POST.get('meeting_link')}")
        
        # Update event details
        event.title = request.POST.get('title')
        event.description = request.POST.get('description')
        event.date = request.POST.get('date')
        event.time = request.POST.get('time')
        event.location = request.POST.get('location')
        event.location_type = request.POST.get('location_type')
        event.capacity = request.POST.get('capacity')
        event.price_type = request.POST.get('price_type')
        event.duration = request.POST.get('duration')
        
        # Handle image deletions
        images_to_delete = request.POST.getlist('delete_images')
        for image_id in images_to_delete:
            try:
                image = EventImage.objects.get(id=image_id)
                image.delete()
            except EventImage.DoesNotExist:
                pass
        
        # Handle new images
        new_images = request.FILES.getlist('new_images')
        for image in new_images:
            EventImage.objects.create(event=event, image=image)
        
        # Handle meeting link for virtual/hybrid events
        if event.location_type in ['virtual', 'hybrid']:
            meeting_link = request.POST.get('meeting_link', '')
            if meeting_link and not meeting_link.startswith(('http://', 'https://')):
                meeting_link = 'https://' + meeting_link
            event.meeting_link = meeting_link

        # Handle cost for paid events
        if event.price_type in ['paid-for', 'self-funded']:
            try:
                event.cost = float(request.POST.get('cost', 0))
            except ValueError:
                event.cost = 0
        else:
            event.cost = None
        
        # Handle tags
        tags = request.POST.get('tags', '').split(',')
        event.tags.clear()
        for tag_name in tags:
            tag_name = tag_name.strip()
            if tag_name:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                event.tags.add(tag)
        
        event.save()
        messages.success(request, 'Event updated successfully!')
        return redirect('event_view', event_id=event_id)
    
    context = {
        'event': event,
        'all_tags': Tag.objects.all(),
        'duration_hours': duration_hours,
        'duration_minutes': duration_minutes,
    }
    return render(request, 'main/event_edit.html', context)


@never_cache
def all_my_events(request):
    user = request.user
    # Get current datetime
    now = timezone.now()
    
    # Get all events created by the user
    created_events = Event.objects.filter(creator=request.user)
    
    # Get all events the user has signed up for
    signed_up_events = Event.objects.filter(eventsignup__user=request.user)
    
    # Combine and remove duplicates
    all_my_events = (created_events | signed_up_events).distinct()
    
    # Sort by date
    all_my_events = all_my_events.order_by('-date')
    
    context = {
        'all_my_events': all_my_events,
        'created_count': created_events.count(),
        'signed_up_count': signed_up_events.count()
    }
    
    return render(request, 'main/all_my_events.html', context)

def clean_unused_tags():
    """Remove tags that aren't associated with any events"""
    Tag.objects.annotate(
        event_count=Count('event')
    ).filter(event_count=0).delete()

@login_required
def event_delete(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.user == event.creator:
        event.delete()
        # Clean up unused tags after event deletion
        clean_unused_tags()
        messages.success(request, 'Event deleted successfully!')
    return redirect('all_events')

@login_required
@csrf_protect
def add_announcement(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if the user is the event creator
    if request.user != event.creator:
        logger.error({
            "message": "Unauthorized announcement attempt",
            "user": request.user.username,
            "event_id": event_id
        })
        messages.error(request, "Only the event creator can post announcements.")
        return redirect('event_view', event_id=event_id)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            try:
                announcement = Announcement.objects.create(
                    event=event,
                    content=content,
                    created_by=request.user
                )
                
                logger.info({
                    "message": "New announcement created",
                    "event_id": event_id,
                    "event_title": event.title,
                    "created_by": request.user.username
                })
                
                logger.add_metric("Announcement Created", {
                    "event_id": event_id,
                    "event_title": event.title
                })
                
                messages.success(request, "Announcement posted successfully!")
            except Exception as e:
                logger.error({
                    "message": f"Error creating announcement: {str(e)}",
                    "event_id": event_id,
                    "user": request.user.username,
                    "error": str(e)
                })
                messages.error(request, "Failed to post announcement. Please try again.")
        else:
            messages.error(request, "Announcement content cannot be empty.")
    
    return redirect('event_view', event_id=event_id)
