"""
Rule-based triage and department recommendation (report Section 3.6).

* Eight departments: Pulmonology, Gastroenterology, General Medicine, Cardiology,
  Dermatology, Neurology, Orthopedics, ENT.
* Inputs: selected symptoms (D1 names) and/or free-text history, plus optional vitals.
* Output: up to four ranked departments, each with a textual justification
  (which words / symptoms triggered it), red-flag alerts and an appointment
  priority (Urgent / High / Routine).
* Priority is computed from D2 symptom-severity weights, red flags and vitals.
  It is deliberately INDEPENDENT of the disease classifier, so an uncertain
  model can never lower the priority of a patient with an emergency symptom.
* Every rule is plain data below, so clinicians can review and edit it
  without retraining any model.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional

DEPARTMENTS = ["Pulmonology", "Gastroenterology", "General Medicine", "Cardiology",
               "Dermatology", "Neurology", "Orthopedics", "ENT"]

# keyword (matched in free text or symptom name) -> weight
DEPT_KEYWORDS: Dict[str, Dict[str, float]] = {
    "Pulmonology": {"breathless": 2, "breath": 1.5, "cough": 1.5, "phlegm": 1.5, "sputum": 2, "wheez": 2,
                    "asthma": 2, "lung": 1.5, "chest_pain": 0.5, "tuberculosis": 2, "pneumonia": 2},
    "Gastroenterology": {"stomach": 1.5, "abdominal": 1.5, "belly": 1.5, "vomit": 1, "nausea": 1, "diarrh": 1.5,
                         "constipation": 1.5, "acidity": 1.5, "indigestion": 1.5, "liver": 2, "yellow": 1.5,
                         "jaundice": 2, "bowel": 1.5, "anal": 1.5, "stool": 1.5, "gases": 1, "ulcer": 1},
    "General Medicine": {"fever": 1, "fatigue": 0.8, "malaise": 0.8, "chills": 0.8, "weight_loss": 0.8,
                         "lethargy": 0.8, "sweating": 0.5, "urine": 1, "micturition": 1.5, "bladder": 1.5,
                         "thyroid": 1.5, "sugar": 1.5, "polyuria": 1.5, "hunger": 1, "dehydration": 1},
    "Cardiology": {"chest_pain": 2, "chest pain": 2, "palpitation": 2, "heart": 2, "fast_heart_rate": 2,
                   "swollen_legs": 1, "prominent_veins": 1, "blood pressure": 1.5, "hypertension": 2},
    "Dermatology": {"skin": 2, "rash": 2, "itch": 1.5, "pimple": 2, "blackhead": 2, "blister": 2, "nail": 1.5,
                    "peeling": 2, "patches": 1.5, "eruption": 2, "sore": 1, "crust": 2, "scurring": 1.5,
                    "red_spots": 1},
    "Neurology": {"headache": 1.5, "dizziness": 1.5, "slurred": 2.5, "weakness_of_one_body_side": 3,
                  "altered_sensorium": 2.5, "coma": 3, "balance": 1.5, "unsteadiness": 1.5,
                  "visual_disturbances": 1.5, "seizure": 3, "numb": 2, "concentration": 1, "stiff_neck": 1},
    "Orthopedics": {"joint": 2, "knee": 2, "hip": 2, "back_pain": 1.5, "back pain": 1.5, "neck_pain": 1.5,
                    "muscle": 1, "movement_stiffness": 1.5, "painful_walking": 2, "fracture": 3, "bone": 2,
                    "cramps": 1},
    "ENT": {"throat": 2, "sneez": 2, "runny_nose": 2, "congestion": 2, "sinus": 2.5, "loss_of_smell": 2,
            "ear": 2, "spinning": 2.5, "vertigo": 2.5, "watering_from_eyes": 1, "patches_in_throat": 2},
}

# symptom -> red-flag alert (always raised, regardless of the classifier)
RED_FLAG_SYMPTOMS: Dict[str, str] = {
    "chest_pain": "Chest pain - exclude acute coronary syndrome (ECG).",
    "breathlessness": "Breathlessness - check SpO2 and respiratory rate.",
    "weakness_of_one_body_side": "One-sided weakness - possible stroke.",
    "slurred_speech": "Slurred speech - possible stroke or hypoglycaemia.",
    "altered_sensorium": "Altered consciousness.",
    "coma": "Unresponsive / coma.",
    "blood_in_sputum": "Coughing blood.",
    "stomach_bleeding": "Gastrointestinal bleeding.",
    "acute_liver_failure": "Signs of acute liver failure.",
    "bloody_stool": "Blood in stool.",
}
RED_FLAG_COMBOS = [
    ({"chest_pain", "sweating"}, "Chest pain with sweating - treat as possible heart attack."),
    ({"chest_pain", "breathlessness"}, "Chest pain with breathlessness."),
    ({"high_fever", "stiff_neck"}, "Fever with stiff neck - exclude meningitis."),
]
# free-text phrases mapped to catalogue symptoms, so combination rules also work on typed history
TEXT_TO_SYMPTOM = {"chest pain": "chest_pain", "chest tightness": "chest_pain", "breathless": "breathlessness",
                   "shortness of breath": "breathlessness", "difficulty breathing": "breathlessness",
                   "sweat": "sweating", "palpitation": "palpitations", "slurred": "slurred_speech",
                   "weakness on one side": "weakness_of_one_body_side", "facial droop": "weakness_of_one_body_side",
                   "stiff neck": "stiff_neck", "high fever": "high_fever", "coughing blood": "blood_in_sputum",
                   "vomiting blood": "stomach_bleeding", "unconscious": "coma"}
RED_FLAG_TEXT = ["chest pain", "difficulty breathing", "shortness of breath", "unconscious", "seizure",
                 "severe bleeding", "stroke", "facial droop", "suicid"]

_SEVERITY: Optional[Dict[str, int]] = None


def _severity() -> Dict[str, int]:
    global _SEVERITY
    if _SEVERITY is None:
        _SEVERITY = {}
        path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "d2", "Symptom_severity.csv")
        if os.path.exists(path):
            with open(path) as f:
                for row in csv.reader(f):
                    if len(row) >= 2 and row[1].strip().isdigit():
                        _SEVERITY[row[0].strip().replace(" ", "_")] = int(row[1])
    return _SEVERITY


def _vital_flags(v: Dict) -> List[str]:
    out = []
    def num(k):
        try:
            return float(v[k]) if v.get(k) not in (None, "") else None
        except (TypeError, ValueError):
            return None
    spo2, temp, sbp, hr = num("spo2"), num("temperature"), num("systolic_bp") or num("blood_pressure"), num("heart_rate")
    if spo2 is not None and spo2 < 92: out.append(f"SpO2 {spo2:.0f}% (< 92%).")
    if temp is not None and temp >= 40: out.append(f"Temperature {temp:.1f} °C (>= 40).")
    if sbp is not None and sbp >= 180: out.append(f"Systolic BP {sbp:.0f} mmHg (>= 180).")
    if sbp is not None and sbp < 90: out.append(f"Systolic BP {sbp:.0f} mmHg (< 90).")
    if hr is not None and (hr >= 130 or hr < 40): out.append(f"Heart rate {hr:.0f} bpm.")
    return out


def triage(symptoms_text: str = "", vitals: Optional[Dict] = None, symptoms: Optional[List[str]] = None) -> Dict:
    vitals = vitals or {}
    symptoms = [s.strip() for s in (symptoms or []) if s]
    text = (symptoms_text or "").lower()
    haystack = [s.lower() for s in symptoms] + ([text] if text else [])

    # -------- department scoring with justification
    scores, why = {d: 0.0 for d in DEPARTMENTS}, {d: [] for d in DEPARTMENTS}
    for dept, kws in DEPT_KEYWORDS.items():
        for kw, w in kws.items():
            hits = [h for h in haystack if kw in h]
            if hits:
                scores[dept] += w
                src = hits[0] if hits[0] != text else f'"{kw}" in history'
                why[dept].append(src.replace("_", " "))
    # combination rules (clinically more specific than single keywords)
    sset0 = set(symptoms) | {sym for phrase, sym in TEXT_TO_SYMPTOM.items() if phrase in text}
    if "chest_pain" in sset0 and ({"sweating", "breathlessness", "fast_heart_rate", "palpitations"} & sset0):
        scores["Cardiology"] += 3; why["Cardiology"].append("chest pain with cardiac features")
    if {"spinning_movements", "loss_of_balance"} <= sset0:
        scores["ENT"] += 2; why["ENT"].append("positional vertigo pattern")
    ranked = sorted([d for d in DEPARTMENTS if scores[d] > 0], key=lambda d: -scores[d])[:4]
    if not ranked:
        ranked = ["General Medicine"]
        why["General Medicine"] = ["no specialty-specific keyword found"]
    total = sum(scores[d] for d in ranked) or 1.0
    recs = [{"department": d, "score": round(scores[d], 2), "share": round(scores[d] / total, 3),
             "justification": "Matched: " + ", ".join(dict.fromkeys(why[d]))} for d in ranked]

    # -------- red flags (independent of classifier)
    sset = set(symptoms) | {sym for phrase, sym in TEXT_TO_SYMPTOM.items() if phrase in text}
    flags = [msg for s, msg in RED_FLAG_SYMPTOMS.items() if s in sset]
    flags += [msg for combo, msg in RED_FLAG_COMBOS if combo <= sset]
    flags += [f'History mentions "{t}".' for t in RED_FLAG_TEXT if t in text]
    flags += _vital_flags(vitals)
    flags = list(dict.fromkeys(flags))

    # -------- priority from D2 severity weights
    sev = _severity()
    weights = [sev.get(s, 3) for s in (sset if sset else symptoms)]
    severity_score = sum(weights)
    max_w = max(weights) if weights else 0
    critical = any(k in " ".join(flags).lower() for k in ("stroke", "heart attack", "coma", "unresponsive",
                                                            "consciousness", "spo2", "bleeding", "meningitis"))
    if critical or len(flags) >= 2:
        priority = "Urgent"
    elif flags or max_w >= 6 or severity_score >= 20:
        priority = "High"
    else:
        priority = "Routine"

    return {
        "department": ranked[0],
        "recommended_departments": recs,
        "top3_departments": [{"department": r["department"], "score": r["score"]} for r in recs[:3]],
        "dept_scores": {k: round(v, 2) for k, v in scores.items()},
        "is_red_flag": bool(flags),
        "red_flag_reasons": flags,
        "priority": priority,
        "severity_score": severity_score,
        "max_symptom_severity": max_w,
        "method": "rule-based keywords + D2 severity weights (independent of the disease model)",
    }
