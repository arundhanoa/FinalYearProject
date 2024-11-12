from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),  # Set landing page as the starting point
    path('about/', views.about, name='about'),
    path('landing/', views.landing, name='landing'),  # Added path for home
    path('login/', views.login_view, name='login'),  # Added path for login
    path('logout/', views.logout_view, name='logout'),
    path('event_create/', views.event_create, name='event_create'),  # Changed from create_event to event_create
    path('event_view/', views.event_view, name='event_view'),
    path('myevents/', views.myevents, name='myevents'),
    path('networking/', views.networking, name='networking'),
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
    path('settings/', views.settings, name='settings'),
    path('settings/update/', views.settings_update, name='settings_update'),  # Add this line
    path('teambuilding/', views.teambuilding, name='teambuilding'),
    path('volunteering/', views.volunteering, name='volunteering'),
    path('help/', views.help_view, name='help'),  # Added path for help
    path('all-events/', views.all_events, name='all_events'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),  # You'll need this for the redirect
]
