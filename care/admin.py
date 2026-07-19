from django.contrib import admin
from .models import Patient, Doctor, Case, SymptomChecklist, CheckIn


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'license_number', 'specialization', 'is_all_rounder', 'experience_years', 'solved_patients', 'created_at')
    list_filter = ('specialization', 'is_all_rounder')
    search_fields = ('name', 'phone_number', 'license_number')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'gender', 'phone_number', 'doctor', 'source_language', 'destination_language', 'created_at')
    list_filter = ('gender', 'source_language', 'destination_language')
    search_fields = ('name', 'phone_number')


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('pk', 'patient', 'doctor', 'status', 'created_at')
    list_filter = ('status', 'doctor')


@admin.register(SymptomChecklist)
class SymptomChecklistAdmin(admin.ModelAdmin):
    list_display = ('symptom_name', 'display_name', 'severity_weight')
    list_editable = ('severity_weight',)


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('case', 'day_number', 'computed_score', 'created_at')
    list_filter = ('day_number',)
