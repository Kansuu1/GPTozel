# backend/model_stub.py
# This is current "model" - a rule-based stub. Replace with XGBoost/LightGBM later.
def predict_signal_from_features(features):
    """
    Return tuple (signal_type:str or None, probability:float)
    probability scale: 0..100 (percentage)
    """
    # Simple rule:
    pc24 = features.get("percent_change_24h") or 0.0
    pc1h = features.get("percent_change_1h") or 0.0
    score = pc24 * 0.5 + pc1h * 0.5  # naive blend
    prob = min(max(abs(score), 0.0), 100.0)
    if prob < 0.5:
        return None, prob
    if score > 0:
        return "LONG", prob
    else:
        return "SHORT", prob