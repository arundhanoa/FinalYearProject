from django.contrib import admin
from .models import Event, Tag, EventImage, EventSignUp, Recommendation

class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'time', 'get_tags')
    
    def get_tags(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])
    
    get_tags.short_description = 'Tags'

admin.site.register(Event, EventAdmin)
admin.site.register(Tag)
admin.site.register(EventImage)
admin.site.register(EventSignUp)
admin.site.register(Recommendation)
