from django.db import migrations

SYMPTOMS = [
    # (symptom_name, display_name, severity_weight 1-5)
    ("fever", "Fever", 4),
    ("cough", "Cough", 2),
    ("headache", "Headache", 2),
    ("weakness", "Weakness / Fatigue", 3),
    ("vomiting", "Vomiting", 3),
    ("breathlessness", "Difficulty Breathing", 5),
    ("chest_pain", "Chest Pain", 5),
    ("body_ache", "Body Ache", 2),
]


def seed_symptoms(apps, schema_editor):
    SymptomChecklist = apps.get_model("care", "SymptomChecklist")
    for name, display, weight in SYMPTOMS:
        SymptomChecklist.objects.get_or_create(
            symptom_name=name,
            defaults={"display_name": display, "severity_weight": weight},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("care", "0002_alter_patient_destination_language_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_symptoms, migrations.RunPython.noop),
    ]
