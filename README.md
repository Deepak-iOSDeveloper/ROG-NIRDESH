# SetuCare — AI-Powered Patient Communication Bridge

SetuCare (setu = bridge in Hindi/Sanskrit) is an AI-powered communication bridge between patients and doctors in India. It addresses two primary problems:
1. Patients struggling to articulate symptoms clearly.
2. Language barriers between rural patients and doctors.

The app uses Groq LLMs (Llama 3) to translate and extract symptoms, and features a custom-built machine learning model to track patient recovery over multiple check-ins to detect early warning signs of worsening health.

## Features
- **Patient Intake Flow**: AI translates patient symptoms from Hindi to English and extracts structured symptoms.
- **Repeatable Check-in Flow**: A structured symptom checklist for tracking patient condition over time.
- **Custom Regression Trend Model**: A hand-written linear regression model (using NumPy and the normal equation) that computes the recovery trend (worsening, improving, stable) and confidence (R²).
- **Doctor Dashboard**: Lists active cases and shows detailed check-in history and trend charts.

## Tech Stack
- Django 5.x, Python 3.11+
- SQLite
- Bootstrap 5 + Chart.js (CDN)
- Groq API (`llama-3.3-70b-versatile`)
- NumPy (Custom ML model)

## Setup Instructions

1. Clone/download the project.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```
   Add your `GROQ_API_KEY` to the `.env` file.
5. Run migrations:
   ```bash
   python manage.py migrate
   ```
6. Seed symptom data:
   ```bash
   python manage.py seed_symptoms
   ```
7. Run the development server:
   ```bash
   python manage.py runserver
   ```
8. Open http://127.0.0.1:8000/ in your browser.

## Project Structure
- `care/models.py`: Data models (Patient, Case, SymptomChecklist, CheckIn, Doctor).
- `care/views.py`: Application logic, including the Groq API call.
- `care/trend_model.py`: Custom ML model for trend analysis.
- `care/templates/`: Django templates for the frontend.

## Custom ML Model
The trend model (`care/trend_model.py`) calculates the recovery trend by applying simple linear regression to patient check-in scores. It does **not** use scikit-learn. It computes the regression parameters (slope, intercept) from scratch using the **normal equation**: `theta = (X^T * X)^-1 * X^T * y`.
It also calculates the R² value to measure the confidence of the trend. Based on the slope and R², the system intelligently classifies the trend and generates alerts for the doctor.

## Demo Notes
This project is built for demonstration purposes. User authentication and login are not implemented. The "day number" during check-ins is manually entered to simulate time passing for demoing the trend analysis quickly.
