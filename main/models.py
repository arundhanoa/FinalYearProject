from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import datetime

# Tag Model
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

# Event Model
class Event(models.Model):
    CATEGORY_CHOICES = [
        ('TB', 'Teambuilding'),
        ('VOL', 'Volunteering'),
        ('NET', 'Networking'),
    ]
    
    LOCATION_CHOICES = [
        ('virtual', 'Virtual'),
        ('in-person', 'In-Person'),
        ('hybrid', 'Hybrid')
    ]
    
    PRICE_CHOICES = [
        ('free', 'Free'),
        ('paid', 'Paid'),
        ('self-funded', 'Self-funded')
    ]
    
    LINE_OF_SERVICE_CHOICES = [
        ('Audit', 'Audit'),
        ('Consulting', 'Consulting'),
        ('Tax', 'Tax'),
        ('Advisory', 'Advisory'),
        ('Assurance', 'Assurance'),
    ]
    
    # Event details
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=200, default='TBD')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_events')
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='events_attending', blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    location_type = models.CharField(
        max_length=20, 
        choices=LOCATION_CHOICES,
        default='in-person'
    )
    price_type = models.CharField(
        max_length=20, 
        choices=PRICE_CHOICES,
        default='self-funded'
    )
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    
    # New fields
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity = models.IntegerField(null=True, blank=True)
    line_of_service = models.CharField(max_length=50, choices=LINE_OF_SERVICE_CHOICES, null=True, blank=True)
    event_type = models.CharField(max_length=100, null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in minutes")
    
    def __str__(self):
        return self.title
    
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

    @property
    def is_expired(self):
        # Convert date and time to datetime object in the current timezone
        event_datetime = timezone.make_aware(
            datetime.combine(self.date, self.time)
        )
        return event_datetime < timezone.now()

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
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
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
    line_of_service = models.CharField(max_length=100)
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
        # Add more offices as needed
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
