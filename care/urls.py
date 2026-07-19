from django.urls import path
from . import views

app_name = 'care'

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),

    # Doctor auth
    path('signup/', views.doctor_signup, name='doctor_signup'),
    path('login/', views.doctor_login, name='doctor_login'),
    path('logout/', views.doctor_logout, name='doctor_logout'),

    # Doctor profile
    path('profile/', views.doctor_profile, name='doctor_profile'),
    path('profile/edit/', views.doctor_profile_edit, name='doctor_profile_edit'),

    # Patient management
    path('intake/', views.patient_intake, name='patient_intake'),
    path('patient/<int:patient_id>/edit/', views.patient_edit, name='patient_edit'),
    path('patient/<int:patient_id>/new-case/', views.patient_new_case, name='patient_new_case'),

    # Case management
    path('case/<int:case_id>/', views.case_detail, name='case_detail'),
    path('case/<int:case_id>/edit/', views.case_edit, name='case_edit'),
    path('case/<int:case_id>/checkin/', views.checkin_form, name='checkin_form'),
    path('case/<int:case_id>/resolve/', views.resolve_case, name='resolve_case'),
    path('case/<int:case_id>/retranslate/', views.retranslate_case, name='retranslate_case'),
    path('checkin/<int:checkin_id>/delete/', views.delete_checkin, name='delete_checkin'),

    # Dashboard & Clustering
    path('dashboard/', views.dashboard, name='dashboard'),
    path('clusters/', views.patient_clusters, name='patient_clusters'),
]
