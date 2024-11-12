from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

# Create your views here.


def all_events(request):
    events = Event.objects.all()
    print(f"Number of events found: {len(events)}")  # Debug print
    print(f"Events: {events}")  # Debug print
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
    print("DEBUG: Login view accessed")
    
    if request.user.is_authenticated:
        print("DEBUG: User already authenticated:", request.user)
        return redirect('homepage')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print("DEBUG: Login attempt for username:", username)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            print("DEBUG: Login successful for user:", user)
            next_url = request.POST.get('next') or request.GET.get('next', '/')
            return redirect(next_url)
        else:
            print("DEBUG: Login failed for username:", username)
            messages.error(request, 'Invalid username or password.')
    
    # Get the 'next' parameter to pass to the template
    next_url = request.GET.get('next', '')
    return render(request, 'main/login.html', {'next': next_url})

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
    # First, check if user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to create an event.')
        return redirect('login')

    if request.method == 'POST':
        print("=============== DEBUG INFO ===============")
        print("POST data received:", request.POST)
        print("FILES received:", request.FILES)
        print("User:", request.user)  # Add this debug line
        print("Is authenticated:", request.user.is_authenticated)  # Add this debug line
        
        try:
            # Create event object but don't save yet
            event = Event(
                title=request.POST['title'],
                description=request.POST['description'],
                date=request.POST['date'],
                time=request.POST['time'],
                location_type=request.POST['location_type'],
                location=request.POST.get('location', ''),
                virtual_link=request.POST.get('virtual_link', ''),
                capacity=request.POST['capacity'],
                line_of_service=request.POST['line_of_service'],
                price_type=request.POST['price_type'],
                creator=request.user  # This should now be a valid User instance
            )

            # Handle cost field
            if request.POST['price_type'] == 'self-funded' and 'cost' in request.POST:
                event.cost = request.POST['cost']

            print("About to save event...")
            event.save()
            print(f"Event saved successfully with ID: {event.id}")

            # Handle images
            if 'images' in request.FILES:
                for image in request.FILES.getlist('images'):
                    event.images.create(image=image)
                print(f"Saved {len(request.FILES.getlist('images'))} images")

            messages.success(request, 'Event created successfully!')
            return redirect('event_detail', event_id=event.id)

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            messages.error(request, f'Error creating event: {str(e)}')
            return render(request, 'main/event_create.html')

    return render(request, 'main/event_create.html')

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'main/event_detail.html', {'event': event})

def logout_view(request):
    logout(request)
    return redirect('homepage')
