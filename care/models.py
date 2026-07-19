from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Doctor(models.Model):
    SPECIALIZATION_CHOICES = [
        ('General Medicine', 'General Medicine'),
        ('Pediatrics', 'Pediatrics'),
        ('Dermatology', 'Dermatology'),
        ('Orthopedics', 'Orthopedics'),
        ('Cardiology', 'Cardiology'),
        ('Neurology', 'Neurology'),
        ('ENT', 'ENT'),
        ('Ophthalmology', 'Ophthalmology'),
        ('Psychiatry', 'Psychiatry'),
        ('Gynecology', 'Gynecology'),
        ('Pulmonology', 'Pulmonology'),
        ('Gastroenterology', 'Gastroenterology'),
        ('Other', 'Other'),
    ]

    LANGUAGE_CHOICES = [
        ('Hindi', 'Hindi'),
        ('English', 'English'),
        ('Bengali', 'Bengali'),
        ('Tamil', 'Tamil'),
        ('Telugu', 'Telugu'),

        ('Odia', 'Odia'),
        ('Kannada', 'Kannada'),
        ('Malayalam', 'Malayalam'),
        ('Punjabi', 'Punjabi'),
        ('Urdu', 'Urdu'),
    ]

    # Auth fields (no password — phone + license is the login)
    phone_number = models.CharField(max_length=15, unique=True)
    license_number = models.CharField(max_length=50, unique=True)

    # Profile fields
    name = models.CharField(max_length=200, default='')
    profile_image = models.ImageField(upload_to='doctor_profiles/', blank=True, null=True)
    specialization = models.CharField(max_length=100, choices=SPECIALIZATION_CHOICES, default='General Medicine')
    is_all_rounder = models.BooleanField(default=False, help_text='Check if the doctor handles all basic diseases')
    solved_patients = models.PositiveIntegerField(default=0, help_text='Number of patients successfully treated')
    experience_years = models.PositiveIntegerField(default=0, help_text='Years of medical experience')
    languages_spoken = models.JSONField(default=list, blank=True, help_text='List of languages the doctor speaks')
    bio = models.TextField(blank=True, default='', help_text='Short biography or professional summary')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.name} ({self.license_number})"


class Patient(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    LANGUAGE_CHOICES = [
        ('Hindi', 'Hindi'),
        ('English', 'English'),
        ('Bengali', 'Bengali'),
        ('Tamil', 'Tamil'),
        ('Telugu', 'Telugu'),

    ]

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='patients')
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=15, default='')
    source_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='Hindi')
    destination_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='English')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.age}, {self.gender}) - Phone: {self.phone_number}"


class Case(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='cases')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='cases')
    illness_description_original = models.TextField()
    illness_description_translated = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Case #{self.pk} - {self.patient.name} (Dr. {self.doctor.name})"


class SymptomChecklist(models.Model):
    symptom_name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    severity_weight = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    class Meta:
        ordering = ['-severity_weight', 'display_name']

    def __str__(self):
        return f"{self.display_name} (weight: {self.severity_weight})"


class CheckIn(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='checkins')
    day_number = models.PositiveIntegerField()
    answers = models.JSONField(default=dict)  # stores {symptom_name: true/false}
    computed_score = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f"Day {self.day_number} check-in for Case #{self.case.pk}"

    def compute_score(self):
        """
        Fetch all SymptomChecklist objects, iterate self.answers,
        sum severity_weight for symptoms marked True, set self.computed_score,
        and return self.computed_score.
        """
        all_symptoms = SymptomChecklist.objects.all()
        total = 0
        for symptom in all_symptoms:
            if self.answers.get(symptom.symptom_name, False):
                total += symptom.severity_weight
        self.computed_score = total
        return self.computed_score
