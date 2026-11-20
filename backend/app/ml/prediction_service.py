"""
prediction_service.py - Thin wrapper kept for backward compatibility.

The old hand-weighted score table that used to live here has been REMOVED.
Every symptom prediction is now produced by the trained neural network in
app/ml/nn_diagnosis_service.py, followed by the clinical reasoning engine in
app/ml/clinical_reasoning.py. There is deliberately no silent fallback: if the
neural network cannot load (for example NumPy is not installed) the API
returns a clear error instead of fake percentages.
"""
from typing import Any, Dict, List, Optional


class PredictionService:
    def predict_symptoms(self, active_symptoms: List[str], clinical: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            from app.ml.nn_diagnosis_service import get_nn_service
        except ImportError as e:  # environment problem - never fake a result
            return {
                "error": ("The neural-network engine could not load: " + str(e) +
                          ". Install it with:  pip install -r requirements-ai.txt  and restart the server."),
                "engine": "unavailable",
            }
        return get_nn_service().diagnose(active_symptoms, clinical or {})


prediction_service = PredictionService()
