"""
noshow_model.py - No-show risk at booking time (report Section 3.6).

Loads the model trained by research/noshow_experiment.py on the Kaggle D3 dataset
(artifacts/research/noshow_model.joblib). If D3 has not been added yet, the
service reports "Not trained" instead of inventing a risk level.
"""
import os
from datetime import date
from typing import Dict, Optional

import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "research", "noshow_model.joblib")


class NoShowService:
    def __init__(self):
        self.art = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None
        print("[NoShow] " + (f"Loaded {self.art['name']} trained on {self.art['dataset']}" if self.art
                             else "Model not trained - add data/d3/KaggleV2-May-2016.csv and run python -m research.run_all"))

    @property
    def trained(self) -> bool:
        return self.art is not None

    def predict(self, age: float, female: int, lead_days: float, appt_weekday: Optional[int] = None,
                sms_received: int = 0, scholarship: int = 0, hypertension: int = 0, diabetes: int = 0,
                alcoholism: int = 0, handicap: int = 0, booking_hour: int = 10,
                prior_appointments: int = 0, prior_noshows: int = 0) -> Dict:
        if not self.trained:
            return {"risk_level": "Not trained", "probability": None,
                    "message": "No-show model needs the Kaggle D3 dataset (data/d3/KaggleV2-May-2016.csv)."}
        if appt_weekday is None:
            appt_weekday = date.today().weekday()
        rate = prior_noshows / prior_appointments if prior_appointments else -1.0
        row = {"age": age, "female": female, "scholarship": scholarship, "hypertension": hypertension,
               "diabetes": diabetes, "alcoholism": alcoholism, "handicap": handicap, "sms_received": sms_received,
               "lead_days": lead_days, "appt_weekday": appt_weekday, "booking_hour": booking_hour,
               "prior_appointments": prior_appointments, "prior_noshows": prior_noshows, "prior_noshow_rate": rate}
        x = np.array([[float(row[f]) for f in self.art["features"]]])
        p = float(self.art["model"].predict_proba(x)[0, 1])
        thr = self.art["thresholds"]
        level = "High" if p >= thr["high"] else "Medium" if p >= thr["medium"] else "Low"
        return {"risk_level": level, "probability": round(p, 4), "model": self.art["name"]}

    # legacy signature used by older routes
    def predict_noshow(self, age, bmi=None, distance_km=None, prev_noshow_count=0, days_until_appt=3,
                       risk_score=None, gender="M") -> str:
        return self.predict(age=age, female=int(str(gender).upper().startswith("F")), lead_days=days_until_appt,
                            prior_appointments=prev_noshow_count, prior_noshows=prev_noshow_count)["risk_level"]


noshow_service: Optional[NoShowService] = None


def get_noshow_service() -> NoShowService:
    global noshow_service
    if noshow_service is None:
        noshow_service = NoShowService()
    return noshow_service
