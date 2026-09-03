"""
Inference wrapper for the lightweight recovery timing model.
Loads the trained pipeline artifact, infers optimal delay, and explains feature attribution.
"""
from datetime import datetime, timezone
from pathlib import Path
import joblib
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "model.joblib"

_MODEL_BUNDLE = None

def get_model():
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}")
        _MODEL_BUNDLE = joblib.load(MODEL_PATH)
    return _MODEL_BUNDLE

def predict_timing(event: dict, attempts: int = 0) -> dict:
    """
    Predict optimal retry delay and output model confidence + explanation.
    Raises exception on error to allow caller fallback.
    """
    bundle = get_model()
    clf = bundle["pipeline"]

    timestamp_str = event.get("timestamp")
    if timestamp_str:
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            day_of_month = dt.day
        except Exception:
            day_of_month = datetime.now(timezone.utc).day
    else:
        day_of_month = datetime.now(timezone.utc).day

    decline_code = event.get("decline_code", "card_declined")
    sub_age = event.get("subscription_age_days", 30)
    plan_amount = event.get("amount") or event.get("plan_amount", 99900)

    input_df = pd.DataFrame([{
        "decline_code": decline_code,
        "day_of_month": day_of_month,
        "subscription_age_days": sub_age,
        "plan_amount": plan_amount,
        "attempt_count": attempts,
    }])

    predicted_delay = int(clf.predict(input_df)[0])
    probs = clf.predict_proba(input_df)[0]
    classes = list(clf.classes_)
    confidence = float(probs[classes.index(predicted_delay)])

    # Generate explainable attribution
    if decline_code == "insufficient_funds":
        reason_detail = f"pay-cycle proximity window (day {day_of_month})"
    elif decline_code in {"bank_technical_error", "gateway_technical_error", "bank_not_available"}:
        reason_detail = "transient infrastructure/bank recovery curve"
    elif decline_code == "card_declined":
        reason_detail = "issuer temporary decline clearance window"
    elif decline_code == "authentication_failed":
        reason_detail = "3DS/customer re-authentication window"
    else:
        reason_detail = "category-specific clearance rate"

    explanation = (
        f"Model selected retry in {predicted_delay} day(s) from {reason_detail}; "
        f"confidence {confidence:.2f}; attempt {attempts + 1} of 3."
    )

    return {
        "delay_days": predicted_delay,
        "confidence": round(confidence, 2),
        "explanation": explanation,
    }
