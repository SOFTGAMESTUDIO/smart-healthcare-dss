"""
XGBoost disease predictor + SHAP KernelExplainer (kept warm in RAM).
Synthetic dataset generated internally for demonstration.
"""
import numpy as np
import pandas as pd
import shap
import joblib
import os
import json
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score

FEATURE_NAMES = [
    "age", "gender", "blood_pressure", "cholesterol",
    "blood_sugar", "bmi", "smoking", "family_history",
    "chest_pain_type", "ecg_result"
]

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

MODEL_PATH = os.path.join(ARTIFACTS_DIR, "disease_xgb.joblib")
SCALER_PATH = os.path.join(ARTIFACTS_DIR, "scaler.joblib")
BG_PATH = os.path.join(ARTIFACTS_DIR, "shap_background.npy")


def generate_synthetic_dataset(n: int = 1200) -> pd.DataFrame:
    np.random.seed(42)
    age = np.random.randint(25, 85, n)
    gender = np.random.randint(0, 2, n)
    bp = np.random.normal(130, 20, n).clip(85, 210)
    chol = np.random.normal(220, 40, n).clip(140, 380)
    bs = np.random.normal(120, 35, n).clip(65, 310)
    bmi = np.random.normal(27, 5, n).clip(14, 48)
    smoking = np.random.binomial(1, 0.28, n)
    fh = np.random.binomial(1, 0.33, n)
    cp = np.random.choice([0, 1, 2, 3], n, p=[0.25, 0.30, 0.25, 0.20])
    ecg = np.random.choice([0, 1, 2], n, p=[0.55, 0.25, 0.20])

    # Realistic risk formula
    risk = (
        0.025 * (age - 40) +
        0.008 * (bp - 120) +
        0.004 * (chol - 200) +
        0.003 * (bs - 100) +
        0.012 * bmi +
        0.18 * smoking +
        0.14 * fh +
        0.09 * cp +
        0.07 * ecg +
        np.random.normal(0, 0.15, n)
    )
    prob = 1 / (1 + np.exp(-risk + 1.2))
    target = (prob > 0.50).astype(int)

    df = pd.DataFrame({
        "age": age, "gender": gender,
        "blood_pressure": bp.round(1), "cholesterol": chol.round(1),
        "blood_sugar": bs.round(1), "bmi": bmi.round(2),
        "smoking": smoking, "family_history": fh,
        "chest_pain_type": cp, "ecg_result": ecg,
        "heart_disease": target
    })
    return df


def train_model():
    df = generate_synthetic_dataset(1200)
    X = df[FEATURE_NAMES].values
    y = df["heart_disease"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"[ML] XGBoost AUC-ROC: {auc:.4f}")

    # Save background dataset for SHAP (15 samples)
    bg = X_train[:15]
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    np.save(BG_PATH, bg)

    return model, scaler, bg


class DiseaseMLService:
    """Singleton ML service — XGBoost + SHAP KernelExplainer warm in RAM."""

    def __init__(self):
        self.model, self.scaler, self.bg_data = self._load_or_train()
        print("[ML] Initializing SHAP KernelExplainer (warm cache)...")
        self.explainer = shap.TreeExplainer(self.model)
        print("[ML] SHAP explainer ready.")

    def _load_or_train(self):
        if all(os.path.exists(p) for p in [MODEL_PATH, SCALER_PATH, BG_PATH]):
            model = joblib.load(MODEL_PATH)
            scaler = joblib.load(SCALER_PATH)
            bg = np.load(BG_PATH)
            print("[ML] Loaded cached model artifacts.")
            return model, scaler, bg
        return train_model()

    def predict(self, features: dict) -> dict:
        """Run prediction + SHAP explanation. Returns risk_score, prediction, shap_values."""
        X_raw = np.array([[
            features.get("age", 50),
            features.get("gender", 0),
            features.get("blood_pressure", 120),
            features.get("cholesterol", 200),
            features.get("blood_sugar", 100),
            features.get("bmi", 25),
            features.get("smoking", 0),
            features.get("family_history", 0),
            features.get("chest_pain_type", 0),
            features.get("ecg_result", 0),
        ]])

        X_scaled = self.scaler.transform(X_raw)
        proba = self.model.predict_proba(X_scaled)[0]
        risk_score = float(proba[1])
        prediction = int(risk_score >= 0.5)

        # SHAP values
        shap_vals = self.explainer.shap_values(X_scaled)
        if isinstance(shap_vals, list):
            sv = shap_vals[1][0]
        else:
            sv = shap_vals[0]

        shap_dict = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in sv]))

        return {
            "risk_score": round(risk_score, 4),
            "disease_predicted": prediction,
            "risk_level": "High" if risk_score >= 0.7 else "Medium" if risk_score >= 0.4 else "Low",
            "shap_values": shap_dict,
            "feature_names": FEATURE_NAMES,
        }


# Module-level singleton (loaded at app startup via lifespan)
ml_service: DiseaseMLService = None

def get_ml_service() -> DiseaseMLService:
    return ml_service
