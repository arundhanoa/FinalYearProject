from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Tag, EventImage, EventSignUp
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
# Create your views here.


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

    context = {
        'events': events,
        'show_expired': show_expired,
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
        'all_tags': Tag.objects.all(),
    }
    
    return render(request, 'main/all_events.html', context)


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
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'attendee_count': attendees.count(),
        'current_user': request.user,
        'attendees': attendees,
    }
    
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
    
    print("\n=== DEBUG INFO ===")
    print(f"Current user: {user.username} (ID: {user.id})")
    
    # Get events created by this user
    created_events = Event.objects.filter(creator=user)
    
    # Check both registration methods
    events_from_attendees = Event.objects.filter(attendees=user)
    events_from_signups = Event.objects.filter(eventsignup__user=user)
    
    # Combine both querysets
    signed_up_events = (events_from_attendees | events_from_signups).distinct()
    
    print("\n=== Registration Details ===")
    print(f"Events from attendees field: {events_from_attendees.count()}")
    print(f"Events from EventSignUp: {events_from_signups.count()}")
    print(f"Total unique events registered: {signed_up_events.count()}")
    
    # List all registrations
    print("\nDetailed Registration Info:")
    print("From attendees field:")
    for event in events_from_attendees:
        print(f"- {event.title} (ID: {event.id})")
    print("\nFrom EventSignUp:")
    for event in events_from_signups:
        print(f"- {event.title} (ID: {event.id})")
    
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
def event_create(request):
    if request.method == 'POST':
        try:
            # Create event with only the fields that exist in your model
            event = Event(
                title=request.POST['title'],
                description=request.POST['description'],
                date=request.POST['date'],
                time=request.POST['time'],
                location=request.POST['location'],
                creator=request.user
            )
            event.save()

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

            messages.success(request, 'Event created successfully!')
            return redirect('all_events')
            
        except Exception as e:
            print(f"Error details: {str(e)}")  # Added for debugging
            messages.error(request, f'Error creating event: {str(e)}')
            return redirect('event_create')
    
    existing_tags = Tag.objects.all()
    return render(request, 'main/event_create.html', {'existing_tags': existing_tags})

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
    query = request.GET.get('term', '')
    tags = Tag.objects.filter(name__icontains=query).values_list('name', flat=True)
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
                signup.delete()
                # Also remove from attendees if present
                event.attendees.remove(user)
                event.save()
                
                print("Action: Unregistered")
                print("- Deleted EventSignUp record")
                print("- Removed from attendees")
                
                messages.success(request, 'Successfully unregistered from the event.')
                return redirect('myevents')
            
            elif not signup:
                # Create both types of registration
                EventSignUp.objects.create(user=user, event=event)
                event.attendees.add(user)
                event.save()
                
                print("Action: Registered")
                print("- Created EventSignUp record")
                print("- Added to attendees")
                
                messages.success(request, 'Successfully registered for the event!')
            
            # Verify registration status after action
            final_signup = EventSignUp.objects.filter(user=user, event=event).exists()
            final_attendee = event.attendees.filter(id=user.id).exists()
            print(f"\nFinal Status:")
            print(f"- EventSignUp record exists: {final_signup}")
            print(f"- In attendees list: {final_attendee}")
            print("=== END DEBUG ===\n")
            
        except IntegrityError:
            messages.error(request, 'You are already registered for this event.')
            print("Error: IntegrityError - Already registered")
        except Exception as e:
            print(f"Error in event_signup: {str(e)}")
            messages.error(request, f'An error occurred: {str(e)}')
    
    # Force reload of the page without cache
    response = redirect('event_view', event_id=event_id)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
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
def event_edit(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Check if the user is the creator of the event
    if event.creator != request.user:
        messages.error(request, "You don't have permission to edit this event.")
        return redirect('event_view', event_id=event_id)
    
    if request.method == 'POST':
        # Update event details
        event.title = request.POST.get('title')
        event.description = request.POST.get('description')
        event.date = request.POST.get('date')
        event.time = request.POST.get('time')
        event.location = request.POST.get('location')
        event.capacity = request.POST.get('capacity')
        event.price_type = request.POST.get('price_type')
        
        # Handle tags
        selected_tags = request.POST.getlist('tags')
        event.tags.clear()
        event.tags.add(*selected_tags)
        
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
        
        event.save()
        messages.success(request, 'Event updated successfully!')
        return redirect('event_view', event_id=event_id)
    
    context = {
        'event': event,
        'all_tags': Tag.objects.all(),
    }
    return render(request, 'main/event_edit.html', context)
