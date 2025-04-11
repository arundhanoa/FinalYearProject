from django.contrib.auth import get_user_model
from django.test import TestCase
from main.models import Event, Tag, EventSignup, EventInterest
from django.contrib.auth import get_user_model
from django.utils import timezone
from recommendations.models import UserEventInteraction
from recommendations.services import HybridRecommender
import random
from datetime import timedelta
import time
from functools import lru_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Tag, EventImage, EventSignUp, Announcement, LOCATION_CHOICES, PRICE_CHOICES
from recommendations.models import UserEventInteraction
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from .forms import CustomUserCreationForm
from django.db import transaction, IntegrityError, models
from django.views.decorators.cache import cache_page
from django.db.models import Prefetch
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import rotate_token
from .models import CustomUser
from django.views.decorators.cache import never_cache
from django.db.models import Count, Q
import logging
RecommendationService = HybridRecommender()
default_recs = 1

recommender = HybridRecommender()
settings = Settings.objects.get(id=1)

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    important = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    target_service = models.CharField(
        max_length=50,
        choices=[
            ('All', 'All Services'),
            ('Audit', 'Audit'),
            ('Tax', 'Tax'),
            ('Consulting', 'Consulting'),
            ('Advisory', 'Advisory'),
        ],
        default='All'
    )
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title