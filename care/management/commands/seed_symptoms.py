from django.core.management.base import BaseCommand
from care.models import SymptomChecklist

class Command(BaseCommand):
    help = 'Pre-populate the SymptomChecklist table with default symptoms and severity weights.'

    SYMPTOMS = [
        ('fever', 'Fever', 5),
        ('cough', 'Cough', 3),
        ('body_ache', 'Body Ache', 3),
        ('headache', 'Headache', 4),
        ('fatigue', 'Fatigue', 2),
        ('nausea', 'Nausea', 3),
        ('rash', 'Rash', 4),
        ('joint_pain', 'Joint Pain', 3),
        ('chills', 'Chills', 4),
        ('loss_of_appetite', 'Loss of Appetite', 2),
    ]

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for symptom_name, display_name, weight in self.SYMPTOMS:
            obj, created = SymptomChecklist.objects.update_or_create(
                symptom_name=symptom_name,
                defaults={
                    'display_name': display_name,
                    'severity_weight': weight,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {created_count} new symptoms, updated {updated_count} existing.'
        ))
        self.stdout.write('Symptoms and weights:')
        for s in SymptomChecklist.objects.all():
            self.stdout.write(f'  • {s.display_name}: weight {s.severity_weight}')
