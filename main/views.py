from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Tag, EventImage
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse

# Create your views here.


def all_events(request):
    events = Event.objects.all()
    
    # Get filter parameters
    sort_by = request.GET.get('sort_by', '-date')
    sort_direction = request.GET.get('direction', 'desc')
    title_filter = request.GET.get('title', '')
    date_filter = request.GET.get('date', '')
    location_filter = request.GET.get('location', '')
    price_type_filter = request.GET.get('price_type', '')
    tag_filter = request.GET.get('tag', '')

    # Apply filters
    if title_filter:
        events = events.filter(title__icontains=title_filter)
    
    if date_filter:
        try:
            events = events.filter(date=date_filter)
        except ValueError:
            pass  # Handle invalid date format
    
    if location_filter:
        events = events.filter(location__icontains=location_filter)
    
    if price_type_filter:
        events = events.filter(price_type=price_type_filter)
    
    if tag_filter:
        events = events.filter(tags__name=tag_filter)
        
    # Apply sorting
    if sort_direction == 'asc':
        events = events.order_by(sort_by.replace('-', ''))
    else:
        events = events.order_by(sort_by)
        
    # Get unique values for dropdowns
    all_tags = Tag.objects.all()
    price_types = Event.objects.values_list('price_type', flat=True).distinct()
    
    context = {
        'events': events,
        'all_tags': all_tags,
        'price_types': price_types,
        'current_filters': {
            'sort_by': sort_by,
            'direction': sort_direction,
            'title': title_filter,
            'date': date_filter,
            'location': location_filter,
            'price_type': price_type_filter,
            'tag': tag_filter
        }
    }
    return render(request, 'main/all_events.html', context)


def homepage(request):
    popular_events = Event.objects.all()[:4]  # Get first 4 events for now
    recommended_events = Event.objects.all()[4:8]  # Get next 4 events
    
    print(f"Number of popular events: {len(popular_events)}")  # Debug print
    print(f"Number of recommended events: {len(recommended_events)}")  # Debug print
    

    context = {
        'popular_events': popular_events,
        'recommended_events': recommended_events,
    }
    return render(request, 'main/homepage.html', context)

def landing(request):
    return render(request, 'main/landing.html')  # Adjust template path as necessary

def about(request):
    return render(request, 'main/about.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to the page they were trying to access
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'main/login.html')

def event_view(request, event_id):
    event = get_object_or_404(Event.objects.prefetch_related('event_images'), id=event_id)
    return render(request, 'main/event_view.html', {'event': event})

@login_required
def myevents(request):
    # Get events created by the user
    created_events = Event.objects.filter(creator=request.user).order_by('-date')
    
    # Get events the user has signed up for
    signed_up_events = Event.objects.filter(participants=request.user).order_by('-date')
    
    # Split each category into popular and recommended
    # For this example, we'll consider newer events as "popular" and older as "recommended"
    created_popular = created_events[:4]
    created_recommended = created_events[4:8]
    
    signed_up_popular = signed_up_events[:4]
    signed_up_recommended = signed_up_events[4:8]
    
    # Add some debug prints
    print(f"Created events count: {created_events.count()}")
    print(f"Signed up events count: {signed_up_events.count()}")
    
    context = {
        'created_popular': created_popular,
        'created_recommended': created_recommended,
        'signed_up_popular': signed_up_popular,
        'signed_up_recommended': signed_up_recommended,
    }
    
    return render(request, 'main/myevents.html', context)

def networking(request):
    return render(request, 'main/networking.html')

def profile(request):
    return render(request, 'main/profile.html')

def register(request):
    return render(request, 'main/register.html')

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
            # Create event
            event = Event(
                title=request.POST['title'],
                description=request.POST['description'],
                date=request.POST['date'],
                time=request.POST['time'],
                location_type=request.POST['location_type'],
                location=request.POST['location'],
                virtual_link=request.POST['virtual_link'],
                capacity=request.POST['capacity'],
                line_of_service=request.POST['line_of_service'],
                price_type=request.POST['price_type'],
                cost=request.POST['cost'] if request.POST['cost'] else None,
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
            return redirect('all_events')  # Redirect to all events page instead
            
        except Exception as e:
            messages.error(request, f'Error creating event: {str(e)}')
            return redirect('event_create')
    
    existing_tags = Tag.objects.all()
    return render(request, 'main/event_create.html', {'existing_tags': existing_tags})

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'main/event_detail.html', {'event': event})

def logout_view(request):
    logout(request)
    return redirect('homepage')

def get_tags(request):
    query = request.GET.get('term', '')
    tags = Tag.objects.filter(name__icontains=query).values_list('name', flat=True)
    return JsonResponse(list(tags), safe=False)

@login_required
def event_signup(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.participants.add(request.user)
    messages.success(request, f'Successfully signed up for {event.title}!')
    return redirect('event_view', event_id=event_id)
