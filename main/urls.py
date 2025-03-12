from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

urlpatterns = [
    path('', views.landing, name='landing'),  # If you want signup as landing page
    path('home/', views.all_events, name='all_events'),
    path('about/', views.about, name='about'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('event_create/', views.event_create, name='event_create'),  # Changed from whatever it was before
    path('event_view/<int:event_id>/', views.event_view, name='event_view'),
    path('myevents/', views.my_events, name='my_events'),
    path('all-my-events/', views.all_my_events, name='all_my_events'),
    path('networking/', views.networking, name='networking'),
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
    path('settings/', views.settings, name='settings'),
    path('settings/update/', views.settings_update, name='settings_update'),  # Add this line
    path('signup/', views.signup, name='signup'),
    path('teambuilding/', views.teambuilding, name='teambuilding'),
    path('volunteering/', views.volunteering, name='volunteering'),
    path('help/', views.help_view, name='help'),  # Added path for help
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),  # You'll need this for tshe redirect
    path('api/tags/', views.get_tags, name='get_tags'),
    path('event_signup/<int:event_id>/', views.event_signup, name='event_signup'),
    path('username/<str:username>/', views.display_username, name='display_username'),
    path('debug-registrations/', views.debug_registrations, name='debug_registrations'),
    path('event/<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('signed-up/past/', views.all_signed_up_past, name='all_signed_up_past'),
    path('signed-up/upcoming/', views.all_signed_up_upcoming, name='all_signed_up_upcoming'),
    path('created/past/', views.all_created_past, name='all_created_past'),
    path('created/upcoming/', views.all_created_upcoming, name='all_created_upcoming'),
    path('event/<int:event_id>/add-announcement/', views.add_announcement, name='add_announcement'),
    path('recommendations/', include('recommendations.urls', namespace='recommendations')),
    path('event/<int:event_id>/join/', views.join_event, name='join_event'),
    path('express-interest/<int:event_id>/', views.express_interest, name='express_interest'),
    path('event/<int:event_id>/leave/', views.leave_event, name='leave_event'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
