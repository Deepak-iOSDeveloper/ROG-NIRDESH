import json
import os
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from dotenv import load_dotenv

load_dotenv()

from .models import Patient, Case, CheckIn, SymptomChecklist, Doctor
from .forms import (
    PatientIntakeForm, CheckInForm, PatientNewCaseForm,
    DoctorSignupForm, DoctorLoginForm, DoctorProfileForm,
    PatientEditForm, CaseEditForm,
)
from .trend_model import fit_linear_regression
from .clustering import cluster_patients


# ---------------------------------------------------------------------------
# Auth decorator — session-based doctor authentication
# ---------------------------------------------------------------------------

def login_required_doctor(view_func):
    """Decorator: require doctor to be logged in via session."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        doctor_id = request.session.get('doctor_id')
        if not doctor_id:
            messages.warning(request, 'Please login to access this page.')
            return redirect('care:doctor_login')
        try:
            request.doctor = Doctor.objects.get(pk=doctor_id)
        except Doctor.DoesNotExist:
            del request.session['doctor_id']
            messages.error(request, 'Session expired. Please login again.')
            return redirect('care:doctor_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_current_doctor(request):
    """Helper to get the currently logged-in doctor or None."""
    doctor_id = request.session.get('doctor_id')
    if doctor_id:
        try:
            return Doctor.objects.get(pk=doctor_id)
        except Doctor.DoesNotExist:
            pass
    return None


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

def home(request):
    """Landing page with navigation to main features."""
    active_cases = Case.objects.filter(status='active').count()
    total_patients = Patient.objects.count()
    total_checkins = CheckIn.objects.count()
    total_doctors = Doctor.objects.count()
    return render(request, 'care/home.html', {
        'active_cases': active_cases,
        'total_patients': total_patients,
        'total_checkins': total_checkins,
        'total_doctors': total_doctors,
    })


def about(request):
    """About page explaining the platform."""
    return render(request, 'care/about.html')


# ---------------------------------------------------------------------------
# Doctor auth — signup / login / logout
# ---------------------------------------------------------------------------

def doctor_signup(request):
    """Doctor registration — phone number + license number only."""
    if request.session.get('doctor_id'):
        return redirect('care:dashboard')

    if request.method == 'POST':
        form = DoctorSignupForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            license_no = form.cleaned_data['license_number']

            # Check if already exists
            if Doctor.objects.filter(phone_number=phone).exists():
                messages.error(request, 'A doctor with this phone number is already registered.')
                return render(request, 'care/signup.html', {'form': form})
            if Doctor.objects.filter(license_number=license_no).exists():
                messages.error(request, 'A doctor with this license number is already registered.')
                return render(request, 'care/signup.html', {'form': form})

            doctor = Doctor.objects.create(
                phone_number=phone,
                license_number=license_no,
            )
            # Auto-login after signup
            request.session['doctor_id'] = doctor.pk
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('care:doctor_profile_edit')
    else:
        form = DoctorSignupForm()

    return render(request, 'care/signup.html', {'form': form})


def doctor_login(request):
    """Doctor login — phone number + license number only."""
    if request.session.get('doctor_id'):
        return redirect('care:dashboard')

    if request.method == 'POST':
        form = DoctorLoginForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            license_no = form.cleaned_data['license_number']

            try:
                doctor = Doctor.objects.get(phone_number=phone, license_number=license_no)
            except Doctor.DoesNotExist:
                messages.error(request, 'Invalid phone number or license number. Please try again.')
                return render(request, 'care/login.html', {'form': form})

            request.session['doctor_id'] = doctor.pk
            messages.success(request, f'Welcome back, Dr. {doctor.name or "Doctor"}!')
            return redirect('care:dashboard')
    else:
        form = DoctorLoginForm()

    return render(request, 'care/login.html', {'form': form})


def doctor_logout(request):
    """Clear doctor session."""
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('care:home')


# ---------------------------------------------------------------------------
# Doctor profile
# ---------------------------------------------------------------------------

@login_required_doctor
def doctor_profile(request):
    """View own doctor profile."""
    return render(request, 'care/doctor_profile.html', {'doctor': request.doctor})


@login_required_doctor
def doctor_profile_edit(request):
    """Edit own doctor profile."""
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=request.doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('care:doctor_profile')
    else:
        form = DoctorProfileForm(instance=request.doctor)

    return render(request, 'care/doctor_profile_edit.html', {'form': form})


# ---------------------------------------------------------------------------
# Patient intake
# ---------------------------------------------------------------------------

@login_required_doctor
def patient_intake(request):
    """Patient intake form — collects demographics + free-text symptoms."""
    if request.method == 'POST':
        form = PatientIntakeForm(request.POST)
        if form.is_valid():
            # Create Patient
            patient = Patient.objects.create(
                doctor=request.doctor,
                name=form.cleaned_data['name'],
                age=form.cleaned_data['age'],
                gender=form.cleaned_data['gender'],
                phone_number=form.cleaned_data['phone_number'],
                source_language=form.cleaned_data['source_language'],
                destination_language=form.cleaned_data['destination_language'],
            )

            raw_text = form.cleaned_data['symptom_description']
            source_language = form.cleaned_data['source_language']
            destination_language = form.cleaned_data['destination_language']

            # Call Groq API for translation + symptom extraction
            try:
                result = call_groq_api(raw_text, source_language, destination_language)
            except Exception as e:
                messages.error(request, f'AI processing failed: {str(e)}. Please try again.')
                return render(request, 'care/patient_intake.html', {'form': form})

            translated_text = result.get('translated_text', raw_text)
            detected_symptoms = result.get('detected_symptoms', {})

            # Create Case
            case = Case.objects.create(
                patient=patient,
                doctor=request.doctor,
                illness_description_original=raw_text,
                illness_description_translated=translated_text,
                status='active',
            )

            # Ensure all 10 symptoms have a value
            all_symptoms = SymptomChecklist.objects.all()
            full_answers = {}
            for s in all_symptoms:
                full_answers[s.symptom_name] = detected_symptoms.get(s.symptom_name, False)

            # Create initial CheckIn (day 0)
            checkin = CheckIn.objects.create(
                case=case,
                day_number=0,
                answers=full_answers,
            )
            checkin.compute_score()
            checkin.save()

            return render(request, 'care/intake_result.html', {
                'patient': patient,
                'case': case,
                'checkin': checkin,
                'translated_text': translated_text,
                'detected_symptoms': full_answers,
                'all_symptoms': all_symptoms,
            })
    else:
        form = PatientIntakeForm()

    return render(request, 'care/patient_intake.html', {'form': form})


# ---------------------------------------------------------------------------
# Groq API call
# ---------------------------------------------------------------------------

def call_groq_api(text, source_language, destination_language):
    """Call Groq API to translate and extract symptoms."""
    from groq import Groq

    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError('GROQ_API_KEY not set in environment. Please add it to your .env file.')

    client = Groq(api_key=api_key)

    symptom_list = ['fever', 'cough', 'body_ache', 'headache', 'fatigue', 'nausea', 'rash', 'joint_pain', 'chills', 'loss_of_appetite']

    system_prompt = f"""You are a medical intake assistant. Your task is to:
1. Translate the patient's input text (from {source_language}) into clear clinical language in {destination_language}.
2. Even if the source and destination languages are the same, clean up the text into a professional medical summary.
3. Analyze the text and determine which of the following 10 symptoms are mentioned or implied:
   fever, cough, body_ache, headache, fatigue, nausea, rash, joint_pain, chills, loss_of_appetite

You MUST respond with ONLY valid JSON in this exact format, no other text:
{{"translated_text": "<clear {destination_language} clinical summary>", "detected_symptoms": {{"fever": true/false, "cough": true/false, "body_ache": true/false, "headache": true/false, "fatigue": true/false, "nausea": true/false, "rash": true/false, "joint_pain": true/false, "chills": true/false, "loss_of_appetite": true/false}}}}

IMPORTANT: Return ONLY the JSON object. No markdown, no explanation, no extra text.
CRITICAL: Output raw UTF-8 characters for the translation (e.g., "আমার" for Bengali, "আমার" is just an example). Do NOT escape non-English characters with unicode escape sequences like \\\\uXXXX."""

    user_prompt = f"Patient's source language: {source_language}\nPatient's symptom description: {text}"

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    response_text = chat_completion.choices[0].message.content.strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        raise ValueError(f'AI returned invalid JSON. Raw response: {response_text[:200]}')

    # Validate structure
    if 'translated_text' not in result:
        result['translated_text'] = text
    if 'detected_symptoms' not in result:
        result['detected_symptoms'] = {s: False for s in symptom_list}

    return result


# ---------------------------------------------------------------------------
# Check-in
# ---------------------------------------------------------------------------

@login_required_doctor
def checkin_form(request, case_id):
    """Check-in form for an existing case — structured symptom yes/no."""
    case = get_object_or_404(Case, pk=case_id)
    symptoms = SymptomChecklist.objects.all()

    if request.method == 'POST':
        form = CheckInForm(request.POST, symptoms=symptoms)
        if form.is_valid():
            day_number = form.cleaned_data['day_number']

            # Build answers dict
            answers = {}
            for s in symptoms:
                answers[s.symptom_name] = form.cleaned_data.get(f'symptom_{s.symptom_name}', False)

            checkin = CheckIn.objects.create(
                case=case,
                day_number=day_number,
                answers=answers,
            )
            checkin.compute_score()
            checkin.save()

            messages.success(request, f'Check-in for Day {day_number} recorded successfully!')
            return redirect('care:case_detail', case_id=case.pk)
    else:
        form = CheckInForm(symptoms=symptoms)

    # Show last check-in day for context
    last_checkin = case.checkins.order_by('-day_number').first()

    return render(request, 'care/checkin_form.html', {
        'form': form,
        'case': case,
        'symptoms': symptoms,
        'last_checkin': last_checkin,
    })


@login_required_doctor
def delete_checkin(request, checkin_id):
    """Delete a specific check-in from history."""
    checkin = get_object_or_404(CheckIn, pk=checkin_id, case__doctor=request.doctor)
    case_id = checkin.case.pk
    
    if request.method == 'POST':
        day_number = checkin.day_number
        checkin.delete()
        messages.success(request, f'Check-in for Day {day_number} deleted successfully.')
        
    return redirect('care:case_detail', case_id=case_id)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required_doctor
def dashboard(request):
    """Doctor dashboard listing all active cases for this doctor."""
    active_cases = Case.objects.filter(
        status='active', doctor=request.doctor
    ).select_related('patient').order_by('-created_at')
    resolved_cases = Case.objects.filter(
        status='resolved', doctor=request.doctor
    ).select_related('patient').order_by('-created_at')

    # Add trend info to each case
    case_data = []
    for case in active_cases:
        checkins = case.checkins.order_by('day_number')
        day_numbers = [c.day_number for c in checkins]
        scores = [c.computed_score for c in checkins]
        trend = fit_linear_regression(day_numbers, scores)
        case_data.append({'case': case, 'trend': trend, 'checkin_count': len(checkins)})

    return render(request, 'care/dashboard.html', {
        'case_data': case_data,
        'resolved_cases': resolved_cases,
    })


# ---------------------------------------------------------------------------
# Case detail
# ---------------------------------------------------------------------------

@login_required_doctor
def case_detail(request, case_id):
    """Detailed view of a single case with check-in history, chart, and trend."""
    case = get_object_or_404(Case, pk=case_id)
    checkins = case.checkins.order_by('day_number')
    symptoms = SymptomChecklist.objects.all()

    day_numbers = [c.day_number for c in checkins]
    scores = [c.computed_score for c in checkins]

    trend = fit_linear_regression(day_numbers, scores)

    # Prepare chart data
    chart_data = {
        'labels': day_numbers,
        'scores': scores,
    }

    # Add regression line if we have enough data
    if trend['slope'] is not None:
        regression_line = [round(trend['intercept'] + trend['slope'] * d, 2) for d in day_numbers]
        chart_data['regression_line'] = regression_line

    return render(request, 'care/case_detail.html', {
        'case': case,
        'checkins': checkins,
        'symptoms': symptoms,
        'trend': trend,
        'chart_data': json.dumps(chart_data),
    })


# ---------------------------------------------------------------------------
# Resolve case
# ---------------------------------------------------------------------------

@login_required_doctor
def resolve_case(request, case_id):
    """Mark a case as resolved."""
    case = get_object_or_404(Case, pk=case_id)
    if request.method == 'POST':
        case.status = 'resolved'
        case.save()

        # Increment doctor's solved_patients count
        request.doctor.solved_patients += 1
        request.doctor.save()

        messages.success(request, f'Case #{case.pk} for {case.patient.name} has been marked as resolved.')
    return redirect('care:dashboard')


# ---------------------------------------------------------------------------
# Patient new case
# ---------------------------------------------------------------------------

@login_required_doctor
def patient_new_case(request, patient_id):
    """Add a new case for an existing patient."""
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = PatientNewCaseForm(request.POST)
        if form.is_valid():
            source_language = form.cleaned_data['source_language']
            destination_language = form.cleaned_data['destination_language']
            raw_text = form.cleaned_data['symptom_description']

            # Call Groq API for translation + symptom extraction
            try:
                result = call_groq_api(raw_text, source_language, destination_language)
            except Exception as e:
                messages.error(request, f'AI processing failed: {str(e)}. Please try again.')
                return render(request, 'care/patient_new_case.html', {'form': form, 'patient': patient})

            translated_text = result.get('translated_text', raw_text)
            detected_symptoms = result.get('detected_symptoms', {})

            # Create Case
            case = Case.objects.create(
                patient=patient,
                doctor=request.doctor,
                illness_description_original=raw_text,
                illness_description_translated=translated_text,
                status='active',
            )

            # Ensure all 10 symptoms have a value
            all_symptoms = SymptomChecklist.objects.all()
            full_answers = {}
            for s in all_symptoms:
                full_answers[s.symptom_name] = detected_symptoms.get(s.symptom_name, False)

            # Create initial CheckIn (day 0)
            checkin = CheckIn.objects.create(
                case=case,
                day_number=0,
                answers=full_answers,
            )
            checkin.compute_score()
            checkin.save()

            # Update patient's languages (if changed for this new incident)
            patient.source_language = source_language
            patient.destination_language = destination_language
            patient.save()

            return render(request, 'care/intake_result.html', {
                'patient': patient,
                'case': case,
                'checkin': checkin,
                'translated_text': translated_text,
                'detected_symptoms': full_answers,
                'all_symptoms': all_symptoms,
            })
    else:
        # Prepopulate with patient's last selected languages
        form = PatientNewCaseForm(initial={
            'source_language': patient.source_language,
            'destination_language': patient.destination_language
        })

    return render(request, 'care/patient_new_case.html', {'form': form, 'patient': patient})


# ---------------------------------------------------------------------------
# Retranslate case
# ---------------------------------------------------------------------------

@login_required_doctor
def retranslate_case(request, case_id):
    """Dynamically re-translate and update symptoms for an existing case."""
    case = get_object_or_404(Case, pk=case_id)
    patient = case.patient

    if request.method == 'POST':
        source_language = request.POST.get('source_language')
        destination_language = request.POST.get('destination_language')

        if source_language and destination_language:
            # Re-run Groq API
            try:
                result = call_groq_api(case.illness_description_original, source_language, destination_language)
            except Exception as e:
                messages.error(request, f'AI processing failed: {str(e)}. Please try again.')
                # Fallback to current values
                all_symptoms = SymptomChecklist.objects.all()
                day_0_checkin = case.checkins.filter(day_number=0).first()
                return render(request, 'care/intake_result.html', {
                    'patient': patient,
                    'case': case,
                    'checkin': day_0_checkin,
                    'translated_text': case.illness_description_translated,
                    'detected_symptoms': day_0_checkin.answers if day_0_checkin else {},
                    'all_symptoms': all_symptoms,
                })

            translated_text = result.get('translated_text', case.illness_description_original)
            detected_symptoms = result.get('detected_symptoms', {})

            # Update Patient languages
            patient.source_language = source_language
            patient.destination_language = destination_language
            patient.save()

            # Update Case translated text
            case.illness_description_translated = translated_text
            case.save()

            # Update or create Day 0 check-in
            all_symptoms = SymptomChecklist.objects.all()
            full_answers = {}
            for s in all_symptoms:
                full_answers[s.symptom_name] = detected_symptoms.get(s.symptom_name, False)

            checkin, created = CheckIn.objects.update_or_create(
                case=case,
                day_number=0,
                defaults={'answers': full_answers}
            )
            checkin.compute_score()
            checkin.save()

            messages.success(request, f'Translation updated successfully to {destination_language}!')

            return render(request, 'care/intake_result.html', {
                'patient': patient,
                'case': case,
                'checkin': checkin,
                'translated_text': translated_text,
                'detected_symptoms': full_answers,
                'all_symptoms': all_symptoms,
            })

    return redirect('care:case_detail', case_id=case.pk)


# ---------------------------------------------------------------------------
# Patient & Case editing (doctor only)
# ---------------------------------------------------------------------------

@login_required_doctor
def patient_edit(request, patient_id):
    """Doctor edits patient details (name, age, gender, phone)."""
    patient = get_object_or_404(Patient, pk=patient_id, doctor=request.doctor)

    if request.method == 'POST':
        form = PatientEditForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient "{patient.name}" updated successfully.')
            return redirect('care:dashboard')
    else:
        form = PatientEditForm(instance=patient)

    return render(request, 'care/patient_edit.html', {'form': form, 'patient': patient})


@login_required_doctor
def case_edit(request, case_id):
    """Doctor edits case/disease details."""
    case = get_object_or_404(Case, pk=case_id, doctor=request.doctor)

    if request.method == 'POST':
        form = CaseEditForm(request.POST, instance=case)
        if form.is_valid():
            form.save()
            messages.success(request, f'Case #{case.pk} updated successfully.')
            return redirect('care:case_detail', case_id=case.pk)
    else:
        form = CaseEditForm(instance=case)

    return render(request, 'care/case_edit.html', {'form': form, 'case': case})


# ---------------------------------------------------------------------------
# Patient clustering
# ---------------------------------------------------------------------------

@login_required_doctor
def patient_clusters(request):
    """Display K-Means clustered patients grouped by symptom similarity."""
    try:
        clusters = cluster_patients()
        error = None
    except ValueError as e:
        clusters = []
        error = str(e)

    return render(request, 'care/patient_clusters.html', {
        'clusters': clusters,
        'error': error,
    })
