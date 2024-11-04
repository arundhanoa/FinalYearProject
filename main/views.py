from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.

def homepage(request):
    return render(request, 'main/homepage.html')

def landing(request):
    return render(request, 'main/landing.html')  # Adjust template path as necessary

def about(request):
    return render(request, 'main/about.html')

def login_view(request):
    return render(request, 'main/login.html')

def event_create(request):
    return render(request, 'main/event_create.html')

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
