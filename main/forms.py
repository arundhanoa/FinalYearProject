# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Event, LOCATION_CHOICES, PRICE_CHOICES

JOB_TITLE_CHOICES = [
    ('', 'Select your job title'),
    ('Associate', 'Associate'),
    ('Senior Associate', 'Senior Associate'),
    ('Manager', 'Manager'),
    ('Senior Manager', 'Senior Manager'),
    ('Director', 'Director'),
    ('Partner', 'Partner'),
    ('Consultant', 'Consultant'),
    ('Senior Consultant', 'Senior Consultant'),
    ('Principal Consultant', 'Principal Consultant'),
]

LINE_OF_SERVICE_CHOICES = [
    ('', 'Select your line of service'),
    ('Audit', 'Audit'),
    ('Consulting', 'Consulting'),
    ('Deals', 'Deals'),
    ('Risk', 'Risk'),
    ('Tax', 'Tax'),
]

OFFICE_CHOICES = [
    ('', 'Select your home office'),
    ('London', 'London'),
    ('Birmingham', 'Birmingham'),
    ('Manchester', 'Manchester'),
    ('Leeds', 'Leeds'),
    ('Bristol', 'Bristol'),
    ('Glasgow', 'Glasgow'),
]

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    other_names = forms.CharField(required=False)
    team = forms.CharField(required=True)
    career_coach = forms.CharField(required=False)
    job_title = forms.ChoiceField(choices=JOB_TITLE_CHOICES, required=True)
    line_of_service = forms.ChoiceField(choices=LINE_OF_SERVICE_CHOICES, required=True)
    home_office = forms.ChoiceField(choices=OFFICE_CHOICES, required=True)
    phone_number = forms.CharField(required=False)

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
        
        # Update field requirements
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['team'].required = True
        self.fields['career_coach'].required = False
        self.fields['phone_number'].required = False
        self.fields['other_names'].required = False

    #generate a unique username by appending numbers if necessary
    def generate_unique_username(self, base_username):
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
            'location_type': forms.Select(choices=LOCATION_CHOICES),
            'price_type': forms.Select(choices=PRICE_CHOICES),
        }