from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Tag
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

# Create your views here.


def all_events(request):
    events = Event.objects.prefetch_related('tags').all()
    
    print("\n=== DEBUG: All Events Tags ===")
    for event in events:
        tags = list(event.tags.all())
        print(f"Event '{event.title}' has tags: {[t.name for t in tags]}")
    print("===========================\n")
    
    return render(request, 'main/all_events.html', {'events': events})


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

def event_view(request):
    return render(request, 'main/event_view.html')

def myevents(request):
    return render(request, 'main/myevents.html')

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
        print("\n=== DEBUG: Creating Event ===")
        
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
        print(f"Event created: {event.title}")

        # Save tags
        tags = request.POST.getlist('tags[]')
        print(f"Processing tags: {tags}")
        for tag_name in tags:
            tag, created = Tag.objects.get_or_create(name=tag_name.strip())
            event.tags.add(tag)
            print(f"Added tag: {tag_name}")

        # Handle images
        images = request.FILES.getlist('images')
        for image in images:
            EventImage.objects.create(event=event, image=image)
        
        print("=== Event Creation Complete ===\n")
        return redirect('event_detail', event_id=event.id)
    
    return render(request, 'main/event_create.html')

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'main/event_detail.html', {'event': event})

def logout_view(request):
    logout(request)
    return redirect('homepage')
