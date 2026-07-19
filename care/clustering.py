"""
Patient Clustering Module — ROGNIRDESH
Uses K-Means (unsupervised) to group patients by symptom similarity.
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .models import Case, CheckIn, SymptomChecklist


# Map dominant symptoms to human-readable cluster names
CLUSTER_NAME_MAP = {
    frozenset(['fever', 'chills']): 'Febrile Syndrome',
    frozenset(['fever', 'body_ache']): 'Febrile Myalgia',
    frozenset(['fever', 'cough']): 'Respiratory Fever',
    frozenset(['cough', 'fatigue']): 'Respiratory Fatigue',
    frozenset(['cough']): 'Respiratory Distress',
    frozenset(['fever']): 'Febrile Illness',
    frozenset(['headache', 'fatigue']): 'Neurological Fatigue',
    frozenset(['headache', 'nausea']): 'Migraine-like Syndrome',
    frozenset(['nausea', 'loss_of_appetite']): 'Gastrointestinal Distress',
    frozenset(['rash', 'joint_pain']): 'Dermatological Arthralgia',
    frozenset(['joint_pain', 'body_ache']): 'Musculoskeletal Pain',
    frozenset(['body_ache', 'fatigue']): 'General Malaise',
    frozenset(['rash']): 'Dermatological Condition',
    frozenset(['fatigue']): 'Chronic Fatigue',
    frozenset(['joint_pain']): 'Joint Disorder',
    frozenset(['nausea']): 'Digestive Disorder',
    frozenset(['headache']): 'Cephalgia',
    frozenset(['chills']): 'Cold Syndrome',
    frozenset(['loss_of_appetite']): 'Appetite Disorder',
    frozenset(['body_ache']): 'Myalgia',
}


def _generate_cluster_name(dominant_symptoms):
    """Generate a human-readable name for a cluster based on its dominant symptoms."""
    if not dominant_symptoms:
        return 'Unclassified Group'

    sym_set = frozenset(dominant_symptoms)

    # Try exact match first
    if sym_set in CLUSTER_NAME_MAP:
        return CLUSTER_NAME_MAP[sym_set]

    # Try subsets (largest first)
    for size in range(min(len(dominant_symptoms), 2), 0, -1):
        for i in range(len(dominant_symptoms)):
            subset = frozenset(dominant_symptoms[:size])
            if subset in CLUSTER_NAME_MAP:
                return CLUSTER_NAME_MAP[subset]

    # Fallback: title-case the first dominant symptom
    display = dominant_symptoms[0].replace('_', ' ').title()
    return f"{display} Group"


def _get_symptom_display_name(symptom_name):
    """Get display name for a symptom."""
    try:
        return SymptomChecklist.objects.get(symptom_name=symptom_name).display_name
    except SymptomChecklist.DoesNotExist:
        return symptom_name.replace('_', ' ').title()


def cluster_patients():
    """
    Cluster active patients by symptom similarity using K-Means.

    Returns:
        list of dicts, each with:
            - cluster_name: str (human-readable)
            - cluster_id: int
            - patients: list of dicts (patient_name, patient_id, case_id, symptoms)
            - dominant_symptoms: list of str (display names)
            - patient_count: int

    Raises:
        ValueError if not enough data for clustering.
    """
    # Get all active cases with their latest check-in
    active_cases = Case.objects.filter(status='active').select_related('patient')

    if active_cases.count() < 4:
        raise ValueError(
            f'Need at least 4 active cases for clustering, found {active_cases.count()}.'
        )

    # Get all symptom names in order
    all_symptoms = list(SymptomChecklist.objects.values_list('symptom_name', flat=True))

    if not all_symptoms:
        raise ValueError('No symptoms defined in the system. Please seed symptoms first.')

    # Build feature matrix: one row per case, columns = symptoms (0/1)
    case_data = []  # (case, feature_vector)
    for case in active_cases:
        latest_checkin = case.checkins.order_by('-day_number').first()
        if latest_checkin is None:
            continue
        feature_vec = []
        for sym_name in all_symptoms:
            feature_vec.append(1 if latest_checkin.answers.get(sym_name, False) else 0)
        case_data.append((case, feature_vec))

    if len(case_data) < 4:
        raise ValueError(
            f'Need at least 4 cases with check-in data, found {len(case_data)}.'
        )

    X = np.array([row[1] for row in case_data])

    # Determine optimal K using silhouette score (range 2..min(6, n-1))
    max_k = min(6, len(case_data) - 1)
    if max_k < 2:
        max_k = 2

    best_k = 2
    best_score = -1.0

    for k in range(2, max_k + 1):
        try:
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X)
            if len(set(labels)) < 2:
                continue
            score = silhouette_score(X, labels)
            if score > best_score:
                best_score = score
                best_k = k
        except Exception:
            continue

    # Final clustering with best K
    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    # Build cluster results
    clusters_raw = {}
    for idx, (case, feat_vec) in enumerate(case_data):
        cluster_id = int(labels[idx])
        if cluster_id not in clusters_raw:
            clusters_raw[cluster_id] = {
                'patients': [],
                'feature_sum': np.zeros(len(all_symptoms)),
            }

        # Gather active symptom display names for this patient
        active_symptoms = [
            _get_symptom_display_name(all_symptoms[i])
            for i in range(len(all_symptoms)) if feat_vec[i] == 1
        ]

        clusters_raw[cluster_id]['patients'].append({
            'patient_name': case.patient.name,
            'patient_id': case.patient.pk,
            'case_id': case.pk,
            'symptoms': active_symptoms,
        })
        clusters_raw[cluster_id]['feature_sum'] += np.array(feat_vec)

    # Build final output with names
    result = []
    for cluster_id, data in sorted(clusters_raw.items()):
        # Find dominant symptoms (top symptom names by sum)
        feat_sum = data['feature_sum']
        top_indices = np.argsort(feat_sum)[::-1]
        dominant_raw = []
        for i in top_indices:
            if feat_sum[i] > 0:
                dominant_raw.append(all_symptoms[i])
            if len(dominant_raw) >= 3:
                break

        cluster_name = _generate_cluster_name(dominant_raw)
        dominant_display = [_get_symptom_display_name(s) for s in dominant_raw]

        result.append({
            'cluster_name': cluster_name,
            'cluster_id': cluster_id,
            'patients': data['patients'],
            'dominant_symptoms': dominant_display,
            'patient_count': len(data['patients']),
        })

    return result
