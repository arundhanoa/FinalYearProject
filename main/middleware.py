from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.contrib.sessions.models import Session
from django.utils import timezone

@receiver(user_logged_out)
def clear_session_on_logout(sender, request, user, **kwargs):
    """Clear any existing sessions for the user on logout"""
    # Delete all sessions for this user
    Session.objects.filter(
        expire_date__gte=timezone.now()
    ).delete() 