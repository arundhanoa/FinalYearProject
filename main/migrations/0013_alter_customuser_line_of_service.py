# Generated by Django 5.1.6 on 2025-02-20 18:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_event_image_alter_event_line_of_service_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='line_of_service',
            field=models.CharField(choices=[('Audit', 'Audit'), ('Tax', 'Tax'), ('Consulting', 'Consulting'), ('Advisory', 'Advisory'), ('Assurance', 'Assurance'), ('All', 'All')], default='All', max_length=50),
        ),
    ]
