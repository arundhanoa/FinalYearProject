from django.core.management.base import BaseCommand
from main.models import CustomUser

class Command(BaseCommand):
    help = 'Fix invalid line of service values for users'

    def handle(self, *args, **kwargs):
        valid_services = [choice[0] for choice in CustomUser.SERVICES]
        
        # Find users with invalid services
        invalid_users = CustomUser.objects.exclude(line_of_service__in=valid_services)
        count = invalid_users.count()
        
        if count:
            self.stdout.write(f"Found {count} users with invalid service lines")
            
            # Update them to 'All'
            invalid_users.update(line_of_service='All')
            
            self.stdout.write(self.style.SUCCESS(f"Updated {count} users to service line 'All'"))
        else:
            self.stdout.write("No invalid service lines found") 