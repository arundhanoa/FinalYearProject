# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Event

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'other_names',
            'work_email',
            'workday_id',
            'line_of_service',
            'team',
            'job_title',
            'line_manager',
            'career_coach',
            'home_office',
            'phone_number',
            'password1',
            'password2',
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']

    def generate_unique_username(self, base_username):
        """Generate a unique username by appending a number if necessary."""
        username = base_username
        counter = 1
        
        while CustomUser.objects.filter(username=username).exists():
            # Append a number to the base username to make it unique
            username = f"{base_username}{counter}"
            counter += 1
            
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Generate base username from first and last name
        first = self.cleaned_data['first_name'].lower()
        last = self.cleaned_data['last_name'].lower()
        base_username = f"{first}.{last}"
        
        # Add other_names if provided
        if self.cleaned_data.get('other_names'):
            other = self.cleaned_data['other_names'].lower()
            base_username = f"{first}.{other}.{last}"
        
        # Generate unique username
        user.username = self.generate_unique_username(base_username)
        
        if commit:
            user.save()
        return user

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'time', 'location', 'location_type', 'price_type']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'tags': forms.CheckboxSelectMultiple(),
            'location_type': forms.Select(choices=Event.LOCATION_CHOICES),
            'price_type': forms.Select(choices=Event.PRICE_CHOICES),
        }