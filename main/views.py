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
from django.db import transaction, IntegrityError, models
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import rotate_token
from .models import CustomUser
from django.views.decorators.cache import never_cache
from django.db.models import Count, Q
import logging

logger = logging.getLogger(__name__)

@never_cache
def all_events(request):
    # Get the show parameter from the URL
    show = request.GET.get('show', 'current')
    
    # Get current datetime
    now = timezone.now()
    
    # Get filter parameters
    sort_by = request.GET.get('sort_by', '-date')
    sort_direction = request.GET.get('direction', 'desc')
    
    # Base queryset with attendee count annotation
    events = Event.objects.annotate(
        attendee_count=Count('attendees', distinct=True)
    )
    
    # Filter based on expired status
    if show == 'expired':
        events = events.filter(date__lt=now.date())
        show_expired = True
    else:
        events = events.filter(date__gte=now.date())
        show_expired = False

    # Handle sorting
    if sort_by in ['popularity', '-popularity']:
        logger.info(f"Sorting by popularity: {sort_by}")
        if sort_by == 'popularity':
            events = events.order_by('attendee_count', 'date')
            logger.info("Sorting by attendee count ascending")
        else:  # '-popularity'
            events = events.order_by('-attendee_count', 'date')
            logger.info("Sorting by attendee count descending")
    else:
        # Validate other sort fields
        valid_sort_fields = ['date', 'title', 'location', '-date', '-title', '-location']
        if sort_by not in valid_sort_fields:
            sort_by = '-date'  # Default to date if invalid sort field
        
        # Apply the sort with direction
        if sort_direction == 'asc':
            events = events.order_by(sort_by.replace('-', ''))
        else:
            events = events.order_by(f"-{sort_by.replace('-', '')}")
        
        logger.info(f"Sorting by: {sort_by} in direction: {sort_direction}")

    # Log the first few events and their attendee counts for debugging
    sample_events = events[:5]
    logger.info("Sample of sorted events:")
    for event in sample_events:
        logger.info(f"Event: {event.title}, Attendees: {event.attendee_count}")
    
    # Get other filter parameters
    title_filter = request.GET.get('title', '')
    date_filter = request.GET.get('date', '')
    time_start = request.GET.get('time_start', '')
    time_end = request.GET.get('time_end', '')
    location_type_filter = request.GET.get('location_type', '')
    price_type_filter = request.GET.get('price_type', '')
    tag_filters = request.GET.getlist('tag')
    capacity_range = request.GET.get('capacity_range', '')
    duration_filter = request.GET.get('duration', '')
    line_of_service_filter = request.GET.get('line_of_service', '')
    event_types = request.GET.getlist('event_type')  # Get multiple event types

    # Apply event type filter
    if event_types:
        if 'General' in event_types:
            events = events.filter(event_type__icontains='General')
        else:
            # Create Q objects for each event type
            event_type_query = Q()
            for event_type in event_types:
                event_type_query |= Q(event_type__icontains=event_type)
            events = events.filter(event_type_query)

    # Apply other filters
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
    
    # Apply tag filters (OR condition)
    if tag_filters:
        tag_query = Q()
        for tag in tag_filters:
            if tag:
                tag_query |= Q(tags__name=tag)
        events = events.filter(tag_query).distinct()
    
    # Filter by capacity range
    if capacity_range:
        if '-' in capacity_range:
            min_capacity, max_capacity = capacity_range.split('-')
            events = events.filter(capacity__gte=min_capacity)
            if max_capacity:
                events = events.filter(capacity__lte=max_capacity)
        elif '+' in capacity_range:
            min_capacity = capacity_range.replace('+', '')
            events = events.filter(capacity__gte=min_capacity)
    
    # Filter by duration
    if duration_filter:
        if '-' in duration_filter:
            min_duration, max_duration = duration_filter.split('-')
            events = events.filter(duration__gte=min_duration)
            if max_duration:
                events = events.filter(duration__lte=max_duration)
        elif '+' in duration_filter:
            min_duration = duration_filter.replace('+', '')
            events = events.filter(duration__gte=min_duration)
    
    # Filter by line of service
    if line_of_service_filter:
        events = events.filter(line_of_service=line_of_service_filter)

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
        'tags': used_tags,
        'current_filters': {
            'sort_by': sort_by,
            'direction': sort_direction,
            'title': title_filter,
            'date': date_filter,
            'time_start': time_start,
            'time_end': time_end,
            'location_type': location_type_filter,
            'price_type': price_type_filter,
            'tag': tag_filters,
            'capacity_range': capacity_range,
            'duration': duration_filter,
            'line_of_service': line_of_service_filter,
            'event_type': event_types,  # Add selected event types to context
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
        event_signups__user=user,
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
        event_signups__user=user,
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
    logger.info("=== Login View Started ===")
    logger.info(f"Request Method: {request.method}")
    logger.info(f"CSRF Cookie Present: {'csrftoken' in request.COOKIES}")
    logger.info(f"Session ID: {request.session.session_key}")
    
    if request.user.is_authenticated:
        logger.info(f"User already authenticated: {request.user.username}")
        return redirect('all_events')
    
    # Ensure CSRF cookie is set
    if not request.COOKIES.get('csrftoken'):
        logger.warning("No CSRF token in cookies, rotating token")
        rotate_token(request)
        
    if request.method == 'POST':
        first_name = request.POST.get('username')
        password = request.POST.get('password')
        
        logger.info(f"Login attempt for username: {first_name}")
        logger.info(f"POST Data: {dict(request.POST)}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        if first_name and password:
            try:
                logger.info("Attempting authentication...")
                user = authenticate(request, username=first_name, password=password)
                
                if user is not None:
                    logger.info(f"Authentication successful for user: {user.username}")
                    login(request, user)
                    logger.info("Login successful, user logged in")
                    return redirect('all_events')
                else:
                    logger.warning(f"Authentication failed for username: {first_name}")
                    messages.error(request, 'Invalid credentials.')
            except Exception as e:
                logger.error(f"Login error occurred: {str(e)}", exc_info=True)
                messages.error(request, 'An error occurred. Please try again.')
        else:
            logger.warning("Missing username or password in POST data")
            messages.error(request, 'Please enter both first name and password.')

    logger.info("Rendering login template")
    response = render(request, 'registration/login.html')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    logger.info("=== Login View Completed ===")
    return response
      

@never_cache
@csrf_protect
def logout_view(request):
    logger.info("=== Logout View Started ===")
    logger.info(f"User attempting logout: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    
    if request.user.is_authenticated:
        logger.info("User is authenticated, proceeding with logout")
        request.session.flush()
        logger.info("Session flushed")
        rotate_token(request)
        logger.info("CSRF token rotated")
        logout(request)
        logger.info("User logged out")
        messages.success(request, 'You have been successfully logged out.')
    else:
        logger.warning("Logout attempted for unauthenticated user")
    
    response = redirect('landing')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    logger.info("=== Logout View Completed ===")
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
    logger.info(f"Event View: {event_view_metadata}")
    
    # Get both general and personal announcements
    announcements = Announcement.objects.filter(
        Q(event=event, for_user__isnull=True) |  # General announcements
        Q(event=event, for_user=request.user)     # Personal announcements
    ).order_by('-created_at')
    
    # Add current date to context for past event checking
    current_date = timezone.now().date()
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'attendee_count': attendees.count(),
        'current_user': request.user,
        'attendees': attendees,
        'announcements': announcements,
        'current_date': current_date,  # Add current date to context
    }

    logger.info(f"Event Views: event_id={event.id}, event_title={event.title}")
    
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
    week_ago = today - timezone.timedelta(days=7)  # For filtering announcements
    user = request.user

    logger.info(f"My Events page accessed by user {user.username} with user id {user.id}")
    
    print("\n=== DEBUG INFO ===")
    print(f"Current user: {user.username} (ID: {user.id})")
    
    # Get events created by this user
    created_events = Event.objects.filter(creator=user)
    
    # Get events user has signed up for
    events_from_signups = Event.objects.filter(
        event_signups__user=user
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
    logger.info(f"User event statistics: {user_stats}")
    
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
    
    # Get all events the user is involved with (for announcements)
    all_user_events = Event.objects.filter(
        Q(creator=user) | Q(event_signups__user=user)
    ).distinct()
    
    # Get announcements for events user is involved with
    relevant_announcements = Announcement.objects.filter(
        Q(event__in=all_user_events) |  # Announcements for events user is involved with
        Q(for_user=user)                # Personal announcements
    ).select_related('event', 'created_by').order_by('-created_at')[:10]
    
    # Get unread announcements for the badge count
    unread_announcements = Announcement.objects.filter(
        Q(event__in=all_user_events) |  # Announcements for events user is involved with
        Q(for_user=user),               # Personal announcements
        read=False
    )
    
    # If the user clicked on the announcements tab, mark announcements as read
    if request.GET.get('tab') == 'announcements':
        # Mark all announcements as read
        unread_announcements.update(read=True)
        
        # If this is an AJAX request, return a success message
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Announcements marked as read',
                'count': 0
            })

    context = {
        'created_past': created_past,
        'created_upcoming': created_upcoming,
        'signed_up_past': signed_up_past,
        'signed_up_upcoming': signed_up_upcoming,
        'relevant_announcements': relevant_announcements,
        'unread_announcements': unread_announcements,  # For badge count
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
            logger.info("New Users: Form data saved")
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
        if cost_value and event.price_type == 'self-funded':
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
        
        # Automatically register the creator for the event
        EventSignUp.objects.create(
            user=request.user,
            event=event,
            signup_date=timezone.now()
        )
        event.attendees.add(request.user)
        
        # Create interaction record for recommendation system
        UserEventInteraction.objects.create(
            user=request.user,
            event=event,
            interaction_type='signup',
            weight=5.0
        )
        
        # Save tags - FIXED: Handle comma-separated string instead of list
        tags_string = request.POST.get('tags', '')
        if tags_string:
            tags_list = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
            print(f"Processing tags: {tags_list}")  # Debug print
            for tag_name in tags_list:
                tag, created = Tag.objects.get_or_create(name=tag_name)
                event.tags.add(tag)
                print(f"Added tag: {tag_name} (created: {created})")  # Debug print

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
            # Check if event is in the past
            if event.date < timezone.now().date():
                # For past events, record interest instead of signup
                UserEventInteraction.objects.create(
                    user=user,
                    event=event,
                    interaction_type='past_interest',
                    weight=3.0
                )
                messages.success(request, 'Your interest in this past event has been recorded.')
                return redirect('event_view', event_id=event_id)

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
                return redirect('event_view', event_id=event_id)
            
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
        if event.price_type == 'self-funded':
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
    
    # Get all events the user has signed up for (using correct field name)
    signed_up_events = Event.objects.filter(event_signups__user=request.user)
    
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
    """
    Allows event creators to post general announcements to all event attendees.
    
    This function implements the following design principles:
    - Security: Only event creators can post announcements (permission check)
    - Validation: Ensures announcement content is not empty
    - Error handling: Comprehensive logging and user feedback
    - Atomic operation: Creates announcement in a single database operation
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Security check: Only allow the event creator to post announcements
    # This prevents unauthorized users from posting to events they don't own
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
        # Validate announcement content is not empty
        if content:
            try:
                # Create the announcement - this will be visible to all event attendees
                # Note: This creates a general announcement (for_user=None) visible to everyone
                announcement = Announcement.objects.create(
                    event=event,
                    content=content,
                    created_by=request.user
                )
                
                # Comprehensive logging for tracking and debugging
                logger.info({
                    "message": "New announcement created",
                    "event_id": event_id,
                    "event_title": event.title,
                    "created_by": request.user.username
                })
                
                logger.info("Announcement Created", {
                    "event_id": event_id,
                    "event_title": event.title
                })
                
                messages.success(request, "Announcement posted successfully!")
            except Exception as e:
                # Exception handling with detailed error logging
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

@login_required
def join_event(request, event_id):
    """
    Handles user registration for events with capacity checks.
    
    This function combines several key operations:
    - Registration validation (prevent duplicate registrations)
    - Capacity enforcement (prevent over-booking)
    - Data consistency (uses transaction to ensure all operations succeed or fail together)
    - Recommendation system integration (records signup interaction for future recommendations)
    """
    event = get_object_or_404(Event, id=event_id)
    
    # Prevent duplicate registrations
    # This avoids database errors and ensures clean UX
    if EventSignUp.objects.filter(user=request.user, event=event).exists():
        messages.info(request, "You are already registered for this event.")
        return redirect('event_view', event_id=event_id)
    
    # Enforce event capacity limits
    # This prevents overbooking and maintains event integrity
    if event.current_participants >= event.capacity:
        messages.error(request, "This event has reached its capacity.")
        return redirect('event_view', event_id=event_id)
    
    # Use database transaction to ensure all operations succeed or fail together
    # This maintains data consistency across related models
    with transaction.atomic():
        # Create the registration record
        EventSignUp.objects.create(
            user=request.user,
            event=event,
            signup_date=timezone.now()
        )
        # Add user to the event's attendees
        event.attendees.add(request.user)
        event.save()
        
        # Record this interaction for the recommendation system
        # This integration allows the system to learn user preferences
        # Signup is weighted highly (5.0) as it indicates strong interest
        UserEventInteraction.objects.update_or_create(
            user=request.user,
            event=event,
            defaults={'interaction_type': 'signup', 'weight': 5.0}
        )
    
    messages.success(request, f"Successfully registered for {event.title}.")
    return redirect('event_view', event_id=event_id)

@login_required
@csrf_protect
def express_interest(request, event_id):
    """
    Allow users to express interest in an event without signing up.
    
    Key features:
    - Lightweight alternative to registration ("soft commitment")
    - Notification system integration (notifies event creator)
    - Recommendation system integration (helps personalize recommendations)
    - Ajax-compatible (returns JSON response for frontend integration)
    """
    if request.method == 'POST':
        try:
            event = get_object_or_404(Event, id=event_id)
            user = request.user
            
            # Record the interest in the recommendation system
            # Uses update_or_create to avoid duplicates if user expresses interest multiple times
            # Weight of 2.0 indicates moderate interest (stronger than a view, weaker than signup)
            interaction, created = UserEventInteraction.objects.update_or_create(
                user=user,
                event=event,
                defaults={
                    'interaction_type': 'interest',
                    'weight': 6.0
                }
            )
            
            # Notify the event creator - helps organizers gauge interest levels
            # This creates a targeted announcement (personal notification)
            notification_message = f"{user.first_name} {user.last_name} expressed interest in your event '{event.title}'"
            Announcement.objects.create(
                event=event,
                content=notification_message,
                created_by=user,
                for_user=event.creator
            )
            
            # Log the interest for analytics and debugging
            logger.info({
                "message": "Interest recorded",
                "user": user.username,
                "event": event.title,
                "event_id": event_id,
                "interaction_created": created
            })
            
            # Return JSON for AJAX requests
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            # Comprehensive error handling
            logger.error({
                "message": "Error recording interest",
                "user": request.user.username,
                "event_id": event_id,
                "error": str(e)
            })
            return JsonResponse({'status': 'error', 'message': 'Failed to record interest'}, status=500)
            
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@csrf_protect
@never_cache
def leave_event(request, event_id):
    """
    Allow users to leave/unregister from an event they previously signed up for.
    
    Key features:
    - Data consistency (uses transaction for related operations)
    - Spot availability notifications (alerts interested users)
    - Recommendation system integration (removes signup interaction)
    - Cache control (ensures page reflects current registration status)
    """
    event = get_object_or_404(Event, id=event_id)
    user = request.user
    
    # Verify the user is actually registered
    signup = EventSignUp.objects.filter(user=user, event=event).first()
    
    if signup:
        try:
            # Use transaction to ensure all database changes succeed or fail together
            # This maintains referential integrity across models
            with transaction.atomic():
                # Clean up all registration records
                signup.delete()
                
                # Remove from attendees M2M relationship
                event.attendees.remove(user)
                
                # Clean up recommendation system data
                UserEventInteraction.objects.filter(
                    user=user,
                    event=event,
                    interaction_type='signup'
                ).delete()
                
                # NOTIFICATION SYSTEM: Alert interested users about the newly available spot
                # This is a key feature that connects the interest tracking and notification systems
                interested_users = UserEventInteraction.objects.filter(
                    event=event,
                    interaction_type='interest'
                ).select_related('user')
                
                # Create personalized notifications for each interested user
                for interaction in interested_users:
                    notification_message = f"A spot has opened up in '{event.title}' that you were interested in!"
                    Announcement.objects.create(
                        event=event,
                        content=notification_message,
                        created_by=event.creator,
                        for_user=interaction.user,
                        read=False
                    )
                
                # Detailed logging for analytics and debugging
                logger.info({
                    "message": "User left event",
                    "user_id": user.id,
                    "username": user.username,
                    "event_id": event.id,
                    "event_title": event.title,
                    "notifications_sent": interested_users.count()
                })
                
                messages.success(request, f"You have successfully unregistered from '{event.title}'.")
        except Exception as e:
            logger.error(f"Error in leave_event: {repr(e)}")
            messages.error(request, f"An error occurred while trying to unregister: {str(e)}")
    else:
        messages.warning(request, "You are not registered for this event.")
    
    # Add cache control headers to ensure the browser always shows current status
    # This prevents the user from seeing stale data
    response = redirect('event_view', event_id=event_id)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
