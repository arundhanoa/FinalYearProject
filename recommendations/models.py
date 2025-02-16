from django.db import models
from django.contrib.auth import get_user_model
from main.models import Event

User = get_user_model()

class UserEventInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    # Interaction types: view, signup, etc.
    interaction_type = models.CharField(max_length=20)
    # Weight of interaction (e.g., view=1, signup=5)
    weight = models.IntegerField(default=1)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'event']),
            models.Index(fields=['interaction_type']),
        ]

class EventSimilarity(models.Model):
    event1 = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='similar_to')
    event2 = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='similar_from')
    similarity_score = models.FloatField()
    
    class Meta:
        indexes = [
            models.Index(fields=['event1', 'event2']),
        ]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Store preprocessed user preferences
    preference_vector = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)

class EventInterest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        indexes = [
            models.Index(fields=['user', 'event']),
        ] 