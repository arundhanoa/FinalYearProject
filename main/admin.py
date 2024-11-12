from django.contrib import admin
from .models import Event, User, Recommendation, EventSignUp

# Register your models here.
admin.site.register(Event)
admin.site.register(Recommendation)
admin.site.register(EventSignUp)
