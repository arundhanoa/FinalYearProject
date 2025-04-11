from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import datetime
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.db.models.signals import pre_save

# Define choices for models
LOCATION_CHOICES = [
    ('in-person', 'In Person'),
    ('virtual', 'Virtual'),
    ('hybrid', 'Hybrid'),
]

PRICE_CHOICES = [
    ('free', 'Free'),
    ('paid', 'Paid'),
    ('self-funded', 'Self Funded'),
    ('company-funded', 'Company Funded'),
]

LINE_OF_SERVICE_CHOICES = [
    ('Audit', 'Audit'),
    ('Tax', 'Tax'),
    ('Consulting', 'Consulting'),
    ('Advisory', 'Advisory'),
    ('Assurance', 'Assurance'),
    ('All', 'All'),
]

# Tag Model - Simple model to store event tags for categorization and filtering
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

# Event Model - Core model for storing event information
# Contains all event details including title, description, date, time, location
# Manages relationships with creators, attendees, and tags
class Event(models.Model):
    # Event details with relationships to users and tags
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=200, default='TBD')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_events')
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='events_attending', blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    location_type = models.CharField(max_length=20, choices=LOCATION_CHOICES,default='in-person')
    price_type = models.CharField(max_length=20, choices=PRICE_CHOICES,default='self-funded')
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity = models.IntegerField(null=True, blank=True)
    line_of_service = models.CharField(max_length=50, choices=LINE_OF_SERVICE_CHOICES, null=True, blank=True)
    event_type = models.CharField(max_length=100, null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in minutes")
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['line_of_service']),
            models.Index(fields=['location_type']),
            # Compound index for common filtering patterns
            models.Index(fields=['date', 'line_of_service']),
        ]
    
    def __str__(self):
        return self.title
    
    # Helper method to format duration into readable string (e.g., "2 hours and 30 minutes")
    def get_duration_display(self):
        """Returns a formatted string of the duration"""
        hours = self.duration // 60
        minutes = self.duration % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        return " and ".join(parts) if parts else "0 minutes"

    # Property to check if event date/time has passed
    @property
    def is_expired(self):
        # Convert date and time to datetime object in the current timezone
        event_datetime = timezone.make_aware(
            datetime.combine(self.date, self.time)
        )
        return event_datetime < timezone.now()

    # Check if event has reached its capacity limit
    def is_full(self):
        """Check if event is at capacity"""
        if self.capacity is None:  # If no capacity set, event is never full
            return False
        return self.attendees.count() >= self.capacity

    # Calculate remaining spots in the event
    def get_available_spots(self):
        """Get number of spots left"""
        if self.capacity is None:  # If no capacity set, show unlimited
            return "Unlimited"
        return max(0, self.capacity - self.attendees.count())

# Event Image Model
class EventImage(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='event_images')
    image = models.ImageField(upload_to='event_images/')

    def __str__(self):
        return f"Image for {self.event.title}"

# Recommendation Model (for Discover and Popular events)
class Recommendation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)  # recommendation score
    
    def __str__(self):
        return f"Recommendation for {self.user.username}: {self.event.title} ({self.score})"

# Registration or Sign-Up for an Event
class EventSignUp(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_signups'
    )
    event = models.ForeignKey(
        Event, 
        on_delete=models.CASCADE,
        related_name='event_signups'
    )
    signup_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Prevents the same user from signing up for the same event multiple times
        unique_together = ['user', 'event']
    
    def __str__(self):
        return f"{self.user.username} signed up for {self.event.title}"
    
class CustomUser(AbstractUser):
    # Optional fields from AbstractUser we'll use:
    # username (comes from AbstractUser)
    # password (comes from AbstractUser)
    # first_name (comes from AbstractUser)
    # last_name (comes from AbstractUser)
    
    # Additional fields
    other_names = models.CharField(max_length=100, blank=True, default='')
    work_email = models.EmailField(unique=True)
    workday_id = models.CharField(max_length=50, unique=True)
    line_of_service = models.CharField(
        max_length=50,
        choices=[
            ('Audit', 'Audit'),
            ('Tax', 'Tax'),
            ('Consulting', 'Consulting'),
            ('Advisory', 'Advisory'),
            ('Assurance', 'Assurance'),
            ('All', 'All')
        ],
        default='All'
    )
    team = models.CharField(max_length=100, blank=True, default='')
    job_title = models.CharField(max_length=100)
    line_manager = models.CharField(max_length=100)
    career_coach = models.CharField(max_length=100)
    
    OFFICE_CHOICES = [
        ('London', 'London'),
        ('Birmingham', 'Birmingham'),
        ('Manchester', 'Manchester'),
        ('Leeds', 'Leeds'),
        ('Bristol', 'Bristol'),
    ]
    
    home_office = models.CharField(
        max_length=50,
        choices=OFFICE_CHOICES
    )
    
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Add related_name to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', 
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['first_name']),
            models.Index(fields=['last_name']),
        ]

class Announcement(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    for_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='personal_announcements'
    )
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event.title} - {self.created_at.strftime('%Y-%m-%d')}"

# Signal handler for managing notifications when attendees change
# Triggers when someone leaves an event and notifies interested users
@receiver(m2m_changed, sender=Event.attendees.through)
def handle_attendee_change(sender, instance, action, pk_set, **kwargs):

    print(f"\n=== ATTENDEE CHANGE DEBUG ===")
    print(f"Action: {action}")
    print(f"Event: {instance.title}")
    print(f"PK Set: {pk_set}")
    
    # Only process when an attendee is removed
    if action == "post_remove":
        event = instance
        print(f"Spot opened in event: {event.title}")
        
        # Check if event has available space
        if not event.is_full():
            print(f"Event is not full, checking for interested users")
            from recommendations.models import UserEventInteraction
            
            # Find users who expressed interest in this event
            interested_interactions = UserEventInteraction.objects.filter(
                event=event,
                interaction_type='interest'
            ).select_related('user')
            
            # Create notifications for interested users about available spot
            print(f"Found {interested_interactions.count()} interested users")
            for interaction in interested_interactions:
                print(f"Creating notification for user: {interaction.user.username}")
                Announcement.objects.create(
                    event=event,
                    content=f"A spot has opened up in '{event.title}'! You can now register for this event.",
                    created_by=event.creator,
                    for_user=interaction.user,
                    read=False
                )

# Signal handler for tracking and notifying about event updates
# Triggers before an event is saved and compares changes to notify attendees
@receiver(pre_save, sender=Event)
def handle_event_update(sender, instance, **kwargs):
    """Signal handler for event updates"""
    try:
        # Get current state of event from database
        old_event = Event.objects.get(pk=instance.pk)
        changes = []
        
        # Helper function to safely compare values, handling None cases
        def values_changed(old_val, new_val):
            if old_val is None and new_val is None:
                return False
            if old_val is None or new_val is None:
                return True
            return str(old_val).strip() != str(new_val).strip()
        
        # Helper function for safe duration conversion
        def safe_duration_convert(duration):
            try:
                return int(duration) if duration is not None else 0
            except (ValueError, TypeError):
                return 0
        
        # Check each field for changes and build change description
        if values_changed(old_event.title, instance.title):
            changes.append(f"title from '{old_event.title}' to '{instance.title}'")
            
        if values_changed(old_event.description, instance.description):
            changes.append("description updated")
            
        if values_changed(old_event.date, instance.date):
            changes.append(f"date from {old_event.date} to {instance.date}")
            
        old_time = old_event.time
        new_time = instance.time
        if isinstance(old_time, str):
            old_time_str = old_time
        else:
            old_time_str = old_time.strftime('%H:%M') if old_time else None
            
        if isinstance(new_time, str):
            new_time_str = new_time
        else:
            new_time_str = new_time.strftime('%H:%M') if new_time else None
            
        if values_changed(old_time_str, new_time_str):
            changes.append(f"time from {old_time_str} to {new_time_str}")
            
        if values_changed(old_event.location, instance.location):
            changes.append(f"location from '{old_event.location}' to '{instance.location}'")
            
        if values_changed(old_event.location_type, instance.location_type):
            changes.append(f"location type from '{old_event.location_type}' to '{instance.location_type}'")
        if values_changed(old_event.meeting_link, instance.meeting_link):
            if not old_event.meeting_link and instance.meeting_link:
                changes.append("meeting link added")
            elif old_event.meeting_link and not instance.meeting_link:
                changes.append("meeting link removed")
            else:
                changes.append("meeting link updated")

        if values_changed(old_event.capacity, instance.capacity):
            old_cap = old_event.capacity if old_event.capacity is not None else 'unlimited'
            new_cap = instance.capacity if instance.capacity is not None else 'unlimited'
            if old_cap != new_cap:
                changes.append(f"capacity from {old_cap} to {new_cap}")
 
        if values_changed(old_event.cost, instance.cost):
            if old_event.cost is None and instance.cost is not None:
                changes.append(f"price set to {instance.cost}")
            elif instance.cost is None and old_event.cost is not None:
                changes.append("price removed")
            elif old_event.cost != instance.cost:
                changes.append(f"price from {old_event.cost} to {instance.cost}")
                
        # Price Type
        if values_changed(old_event.price_type, instance.price_type):
            changes.append(f"price type from '{old_event.price_type}' to '{instance.price_type}'")
            
        # Line of Service
        if values_changed(old_event.line_of_service, instance.line_of_service):
            changes.append(f"line of service from '{old_event.line_of_service}' to '{instance.line_of_service}'")
            
        # Event Type
        if values_changed(old_event.event_type, instance.event_type):
            changes.append(f"event type from '{old_event.event_type}' to '{instance.event_type}'")
            
        # Duration
        old_duration = safe_duration_convert(old_event.duration)
        new_duration = safe_duration_convert(instance.duration)
        if old_duration != new_duration:
            old_hours = old_duration // 60
            old_minutes = old_duration % 60
            new_hours = new_duration // 60
            new_minutes = new_duration % 60
            
            def format_duration(hours, minutes):
                parts = []
                if hours > 0:
                    parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                if minutes > 0:
                    parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
                return " and ".join(parts) if parts else "0 minutes"
            
            old_duration_str = format_duration(old_hours, old_minutes)
            new_duration_str = format_duration(new_hours, new_minutes)
            changes.append(f"duration from {old_duration_str} to {new_duration_str}")
            
        # Image
        if values_changed(old_event.image, instance.image):
            if not old_event.image and instance.image:
                changes.append("image added")
            elif old_event.image and not instance.image:
                changes.append("image removed")
            else:
                changes.append("image updated")
        
        # If any changes detected, notify all event attendees
        if changes:
            change_description = ", ".join(changes)
            for attendee in old_event.attendees.all():
                Announcement.objects.create(
                    event=instance,
                    content=f"Important: Event '{instance.title}' has been updated. Changes made to: {change_description}",
                    created_by=instance.creator,
                    for_user=attendee,
                    read=False
                )
    except Event.DoesNotExist:
        # Skip for new events being created
        pass
