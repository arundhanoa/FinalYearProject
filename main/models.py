from django.db import models
from django.contrib.auth.models import User

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
        ('Virtual', 'Virtual'),
        ('In-person', 'In-person'),
        ('Hybrid', 'Hybrid'),
    ]
    
    # Event details
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location_type = models.CharField(max_length=20)  # virtual, in-person, hybrid
    location = models.CharField(max_length=200, blank=True, null=True)
    virtual_link = models.URLField(blank=True, null=True)
    capacity = models.IntegerField()
    line_of_service = models.CharField(max_length=50)
    price_type = models.CharField(max_length=20)  # free, self-funded, paid
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return self.title

# Event Image Model
class EventImage(models.Model):
    event = models.ForeignKey(Event, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='event_images/')

# Recommendation Model (for Discover and Popular events)
class Recommendation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)  # recommendation score
    
    def __str__(self):
        return f"Recommendation for {self.user.username}: {self.event.title} ({self.score})"

# Registration or Sign-Up for an Event
class EventSignUp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    signup_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Prevents the same user from signing up for the same event multiple times
        unique_together = ['user', 'event']
    
    def __str__(self):
        return f"{self.user.username} signed up for {self.event.title}"