from django import forms
from .models import Patient, Doctor, Case


class DoctorSignupForm(forms.Form):
    """Simple signup — phone number + license number only."""
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 10-digit phone number',
            'pattern': '[0-9]{10,15}',
        })
    )
    license_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your medical license number',
        })
    )


class DoctorLoginForm(forms.Form):
    """Simple login — phone number + license number only."""
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Registered phone number',
        })
    )
    license_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Registered license number',
        })
    )


class DoctorProfileForm(forms.ModelForm):
    """Form for editing the doctor's full profile."""
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

    languages_spoken = forms.MultipleChoiceField(
        choices=LANGUAGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = Doctor
        fields = [
            'name', 'profile_image', 'specialization', 'is_all_rounder',
            'experience_years', 'solved_patients', 'languages_spoken', 'bio',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'profile_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'specialization': forms.Select(attrs={'class': 'form-select'}),
            'is_all_rounder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'solved_patients': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell patients about yourself...'}),
        }


class PatientIntakeForm(forms.Form):
    name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Patient full name'}))
    age = forms.IntegerField(min_value=0, max_value=150, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}))
    gender = forms.ChoiceField(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], widget=forms.Select(attrs={'class': 'form-select'}))
    phone_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Patient phone number',
            'pattern': '[0-9]{10,15}',
        })
    )
    LANGUAGE_CHOICES = [
        ('Hindi', 'Hindi'),
        ('English', 'English'),
        ('Bengali', 'Bengali'),
        ('Tamil', 'Tamil'),
        ('Telugu', 'Telugu'),

    ]
    source_language = forms.ChoiceField(choices=LANGUAGE_CHOICES, initial='Hindi', widget=forms.Select(attrs={'class': 'form-select'}))
    destination_language = forms.ChoiceField(choices=LANGUAGE_CHOICES, initial='English', widget=forms.Select(attrs={'class': 'form-select'}))
    symptom_description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe symptoms in your source language...\n\nExample (Hindi): mujhe bukhar hai aur sar mein dard ho raha hai\nExample (English): I have been having fever and headache for 3 days'}))


class CheckInForm(forms.Form):
    day_number = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5, 10, 15...'}))
    # Symptom fields will be added dynamically in __init__

    def __init__(self, *args, symptoms=None, **kwargs):
        super().__init__(*args, **kwargs)
        if symptoms:
            for symptom in symptoms:
                self.fields[f'symptom_{symptom.symptom_name}'] = forms.BooleanField(
                    required=False,
                    label=symptom.display_name,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})
                )


class PatientNewCaseForm(forms.Form):
    LANGUAGE_CHOICES = [
        ('Hindi', 'Hindi'),
        ('English', 'English'),
        ('Bengali', 'Bengali'),
        ('Tamil', 'Tamil'),
        ('Telugu', 'Telugu'),

    ]
    source_language = forms.ChoiceField(choices=LANGUAGE_CHOICES, initial='Hindi', widget=forms.Select(attrs={'class': 'form-select'}))
    destination_language = forms.ChoiceField(choices=LANGUAGE_CHOICES, initial='English', widget=forms.Select(attrs={'class': 'form-select'}))
    symptom_description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': "Describe the patient's new symptoms or issues..."}))


class PatientEditForm(forms.ModelForm):
    """Form for doctor to edit patient details."""
    class Meta:
        model = Patient
        fields = ['name', 'age', 'gender', 'phone_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
        }


class CaseEditForm(forms.ModelForm):
    """Form for doctor to edit case/disease details."""
    class Meta:
        model = Case
        fields = ['illness_description_original', 'status']
        widgets = {
            'illness_description_original': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
