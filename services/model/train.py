"""
Train a lightweight, interpretable recovery timing model.
Grounded in §2 industry benchmarks:
- insufficient_funds: aligns with pay-cycle windows (beginning/middle/end of month) -> optimal delay ~5 days
- card_declined / issuer holds: typically clear in 24-48 hours -> optimal delay ~2 days
- transient bank/gateway technical errors: immediate/transient -> optimal delay ~1 day
"""
import os
import random
import joblib
import numpy as np
from pathlib import Path
from sklearn.tree import DecisionTreeClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "model.joblib"

DECLINES = [
    "insufficient_funds",
    "card_declined",
    "bank_technical_error",
    "gateway_technical_error",
    "bank_not_available",
    "authentication_failed",
]

def generate_training_data(n_samples=5000, seed=42):
    rng = random.Random(seed)
    X = []
    y = []

    for _ in range(n_samples):
        code = rng.choice(DECLINES)
        day_of_month = rng.randint(1, 31)
        sub_age = rng.randint(1, 720)
        plan_amount = rng.choice([49900, 99900, 149900, 299900])
        attempt = rng.randint(0, 2)

        # Ground truth optimal timing logic grounded in §2:
        # Payday proximity: around 1st-5th, 14th-16th, or 28th-31st
        payday_proximity = (
            min(abs(day_of_month - 1), abs(day_of_month - 30)) <= 3
            or abs(day_of_month - 15) <= 2
        )

        if code == "insufficient_funds":
            delay = 5 if not payday_proximity else 3
        elif code in {"bank_technical_error", "gateway_technical_error", "bank_not_available"}:
            delay = 1
        elif code == "card_declined":
            delay = 2
        elif code == "authentication_failed":
            delay = 1
        else:
            delay = 2

        if rng.random() < 0.05:
            delay = rng.choice([1, 2, 5])

        X.append({
            "decline_code": code,
            "day_of_month": day_of_month,
            "subscription_age_days": sub_age,
            "plan_amount": plan_amount,
            "attempt_count": attempt,
        })
        y.append(delay)

    return X, y

def train_and_export():
    import pandas as pd
    X, y = generate_training_data()
    df = pd.DataFrame(X)

    categorical_features = ["decline_code"]
    numeric_features = ["day_of_month", "subscription_age_days", "plan_amount", "attempt_count"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numeric_features),
        ]
    )

    clf = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", DecisionTreeClassifier(max_depth=5, min_samples_leaf=20, random_state=42))
    ])

    clf.fit(df, y)

    payload = {
        "pipeline": clf,
        "classes": list(clf.classes_),
        "version": "1.0.0",
    }
    joblib.dump(payload, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return clf

if __name__ == "__main__":
    train_and_export()
