from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('recommended/', views.recommended_events, name='recommended_events'),
    path('record-interaction/<int:event_id>/', 
         views.record_event_interaction, 
         name='record_interaction'),
    path('record-interest/<int:event_id>/',
         views.record_event_interest,
         name='record_interest'),
    path('verify/', views.verify_recommendations, name='verify_recommendations'),
] 