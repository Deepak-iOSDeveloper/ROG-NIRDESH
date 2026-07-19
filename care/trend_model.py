import numpy as np

def fit_linear_regression(day_numbers, scores):
    """
    Fit simple linear regression using the normal equation.
    
    Parameters:
        day_numbers: list of int (e.g. [0, 5, 10, 15])
        scores: list of int/float (e.g. [12, 8, 5, 3])
    
    Returns:
        dict with keys: slope, intercept, r_squared, classification, alert
    """
    if len(day_numbers) < 2:
        return {
            'slope': None,
            'intercept': None,
            'r_squared': None,
            'classification': 'NOT_ENOUGH_DATA',
            'alert': False,
            'message': 'Not enough data yet — need at least 2 check-ins.'
        }
    
    x = np.array(day_numbers, dtype=float)
    y = np.array(scores, dtype=float)
    
    # Build design matrix X_b = [[1, x1], [1, x2], ...]
    X_b = np.column_stack([np.ones(len(x)), x])
    
    # Normal equation: theta = (X_b.T @ X_b)^(-1) @ X_b.T @ y
    try:
        theta = np.linalg.inv(X_b.T @ X_b) @ X_b.T @ y
    except np.linalg.LinAlgError:
        return {
            'slope': 0.0,
            'intercept': float(np.mean(y)),
            'r_squared': 0.0,
            'classification': 'STABLE',
            'alert': False,
            'message': 'Unable to compute trend (singular matrix). Classified as STABLE.'
        }
    
    intercept = theta[0]
    slope = theta[1]
    
    # Predictions
    y_pred = X_b @ theta
    
    # R² = 1 - SS_res / SS_tot
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    
    if ss_tot == 0:
        r_squared = 1.0 if ss_res == 0 else 0.0
    else:
        r_squared = 1.0 - (ss_res / ss_tot)
    
    # Classification
    SLOPE_THRESHOLD = 0.5
    if slope > SLOPE_THRESHOLD:
        classification = 'WORSENING'
    elif slope < -SLOPE_THRESHOLD:
        classification = 'IMPROVING'
    else:
        classification = 'STABLE'
    
    # Alert: only if WORSENING and R² > 0.5
    alert = (classification == 'WORSENING' and r_squared > 0.5)
    
    # Build message
    r_pct = round(r_squared * 100)
    message = f"{classification} (trend confidence: {r_pct}%)"
    if alert:
        message = f"⚠️ {message} — recommend early follow-up"
    
    return {
        'slope': round(float(slope), 4),
        'intercept': round(float(intercept), 4),
        'r_squared': round(float(r_squared), 4),
        'classification': classification,
        'alert': alert,
        'message': message
    }
