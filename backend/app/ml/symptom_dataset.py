"""
symptom_dataset.py - Clinical knowledge for all 41 diseases (NOT training data).

The disease model is trained on the real D1 dataset (research/d1_data.py).
This module only provides clinical-knowledge context used by the reasoning
report: typical vitals/age/duration per disease, departments, urgency,
descriptions and precautions, plus the clinical form fields.

Each disease has:
  * symptoms   : typical symptoms; the first ones listed are the HALLMARK symptoms
  * age        : (mean, sd) typical age at presentation
  * female     : probability patient is female
  * temp       : (mean, sd) body temperature in C
  * hr         : (mean, sd) heart rate (bpm)
  * sbp        : (mean, sd) systolic blood pressure (mmHg)
  * spo2       : (mean, sd) oxygen saturation (%)
  * days       : (low, high) typical symptom duration before visit, in days

These values are approximate clinical knowledge used for plausibility checks only.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.ml.disease_kb import SYMPTOMS_131, DISEASES_41

# ----------------------------------------------------------------- profiles
N = (37.0, 0.3)       # normal temperature
FEV = (38.8, 0.6)     # febrile
LOWF = (37.9, 0.4)    # low grade fever

DISEASE_PROFILES: Dict[str, dict] = {
    "Fungal infection": dict(symptoms=["itching", "skin_rash", "nodal_skin_eruptions", "dischromic_patches"],
                             age=(32, 14), female=0.5, temp=N, hr=(78, 8), sbp=(120, 10), spo2=(98, 1), days=(7, 60)),
    "Allergy": dict(symptoms=["continuous_sneezing", "watering_from_eyes", "shivering", "chills"],
                    age=(28, 13), female=0.5, temp=N, hr=(80, 8), sbp=(118, 10), spo2=(98, 1), days=(1, 14)),
    "GERD": dict(symptoms=["acidity", "stomach_pain", "chest_pain", "ulcers_on_tongue", "vomiting", "cough"],
                 age=(42, 13), female=0.5, temp=N, hr=(78, 8), sbp=(124, 12), spo2=(98, 1), days=(14, 180)),
    "Chronic cholestasis": dict(symptoms=["itching", "yellowish_skin", "yellowing_of_eyes", "vomiting", "nausea", "loss_of_appetite", "abdominal_pain"],
                                age=(50, 12), female=0.6, temp=N, hr=(80, 8), sbp=(122, 12), spo2=(97, 1), days=(30, 180)),
    "Drug Reaction": dict(symptoms=["skin_rash", "itching", "burning_micturition", "spotting_urination", "stomach_pain"],
                          age=(40, 16), female=0.55, temp=LOWF, hr=(86, 10), sbp=(120, 12), spo2=(98, 1), days=(1, 7)),
    "Peptic ulcer diseae": dict(symptoms=["abdominal_pain", "indigestion", "passage_of_gases", "internal_itching", "vomiting", "loss_of_appetite"],
                                age=(45, 13), female=0.45, temp=N, hr=(82, 9), sbp=(120, 12), spo2=(98, 1), days=(14, 120)),
    "AIDS": dict(symptoms=["muscle_wasting", "patches_in_throat", "extra_marital_contacts", "high_fever"],
                 age=(35, 10), female=0.4, temp=LOWF, hr=(88, 10), sbp=(115, 12), spo2=(96, 2), days=(30, 365)),
    "Diabetes": dict(symptoms=["polyuria", "irregular_sugar_level", "excessive_hunger", "increased_appetite", "weight_loss",
                               "fatigue", "blurred_and_distorted_vision", "obesity", "restlessness", "lethargy"],
                     age=(52, 12), female=0.48, temp=N, hr=(82, 9), sbp=(132, 14), spo2=(97, 1), days=(30, 365)),
    "Gastroenteritis": dict(symptoms=["diarrhoea", "vomiting", "dehydration", "sunken_eyes"],
                            age=(25, 18), female=0.5, temp=LOWF, hr=(98, 12), sbp=(108, 12), spo2=(98, 1), days=(1, 4)),
    "Bronchial Asthma": dict(symptoms=["breathlessness", "cough", "mucoid_sputum", "family_history", "fatigue", "high_fever"],
                             age=(26, 15), female=0.5, temp=N, hr=(100, 12), sbp=(120, 12), spo2=(93, 2.5), days=(1, 30)),
    "Hypertension": dict(symptoms=["headache", "dizziness", "chest_pain", "loss_of_balance", "lack_of_concentration"],
                         age=(56, 11), female=0.45, temp=N, hr=(84, 10), sbp=(162, 14), spo2=(97, 1), days=(7, 180)),
    "Migraine": dict(symptoms=["headache", "visual_disturbances", "blurred_and_distorted_vision", "stiff_neck", "irritability",
                               "acidity", "indigestion", "excessive_hunger", "depression"],
                     age=(32, 10), female=0.72, temp=N, hr=(80, 8), sbp=(120, 10), spo2=(98, 1), days=(1, 5)),
    "Cervical spondylosis": dict(symptoms=["neck_pain", "back_pain", "weakness_in_limbs", "dizziness", "loss_of_balance"],
                                 age=(54, 10), female=0.5, temp=N, hr=(76, 8), sbp=(128, 12), spo2=(98, 1), days=(30, 365)),
    "Paralysis (brain hemorrhage)": dict(symptoms=["weakness_of_one_body_side", "altered_sensorium", "headache", "vomiting"],
                                         age=(62, 11), female=0.45, temp=N, hr=(90, 14), sbp=(175, 20), spo2=(95, 2), days=(0, 1)),
    "Jaundice": dict(symptoms=["yellowish_skin", "dark_urine", "itching", "abdominal_pain", "vomiting", "fatigue", "weight_loss", "high_fever"],
                     age=(38, 16), female=0.5, temp=LOWF, hr=(86, 9), sbp=(118, 12), spo2=(97, 1), days=(3, 30)),
    "Malaria": dict(symptoms=["high_fever", "chills", "sweating", "muscle_pain", "headache", "vomiting", "nausea", "diarrhoea"],
                    age=(30, 15), female=0.45, temp=(39.4, 0.6), hr=(104, 12), sbp=(112, 12), spo2=(96, 2), days=(2, 10)),
    "Chicken pox": dict(symptoms=["red_spots_over_body", "itching", "skin_rash", "mild_fever", "swelled_lymph_nodes", "fatigue",
                                  "lethargy", "high_fever", "headache", "loss_of_appetite", "malaise"],
                        age=(12, 8), female=0.5, temp=LOWF, hr=(96, 12), sbp=(110, 10), spo2=(98, 1), days=(1, 7)),
    "Dengue": dict(symptoms=["high_fever", "pain_behind_the_eyes", "joint_pain", "muscle_pain", "red_spots_over_body", "skin_rash",
                             "chills", "vomiting", "fatigue", "headache", "nausea", "loss_of_appetite", "back_pain", "malaise"],
                   age=(28, 14), female=0.5, temp=(39.3, 0.6), hr=(98, 12), sbp=(108, 14), spo2=(97, 1.5), days=(2, 7)),
    "Typhoid": dict(symptoms=["high_fever", "toxic_look_(typhos)", "belly_pain", "constipation", "abdominal_pain", "headache",
                              "chills", "vomiting", "fatigue", "nausea", "diarrhoea"],
                    age=(25, 13), female=0.5, temp=(39.0, 0.5), hr=(88, 10), sbp=(112, 12), spo2=(97, 1), days=(5, 21)),
    "hepatitis A": dict(symptoms=["yellowing_of_eyes", "yellowish_skin", "dark_urine", "mild_fever", "joint_pain", "vomiting",
                                  "nausea", "loss_of_appetite", "abdominal_pain", "diarrhoea", "muscle_pain"],
                        age=(22, 12), female=0.5, temp=LOWF, hr=(88, 10), sbp=(116, 12), spo2=(97, 1), days=(3, 21)),
    "Hepatitis B": dict(symptoms=["receiving_blood_transfusion", "receiving_unsterile_injections", "yellowish_skin", "yellow_urine",
                                  "yellowing_of_eyes", "dark_urine", "itching", "fatigue", "lethargy", "loss_of_appetite", "abdominal_pain", "malaise"],
                        age=(38, 13), female=0.45, temp=LOWF, hr=(84, 10), sbp=(118, 12), spo2=(97, 1), days=(14, 120)),
    "Hepatitis C": dict(symptoms=["yellowish_skin", "yellowing_of_eyes", "family_history", "fatigue", "nausea", "loss_of_appetite"],
                        age=(45, 13), female=0.45, temp=N, hr=(80, 9), sbp=(120, 12), spo2=(97, 1), days=(30, 365)),
    "Hepatitis D": dict(symptoms=["yellowish_skin", "dark_urine", "joint_pain", "yellowing_of_eyes", "vomiting", "fatigue",
                                  "nausea", "loss_of_appetite", "abdominal_pain"],
                        age=(36, 12), female=0.45, temp=LOWF, hr=(86, 10), sbp=(118, 12), spo2=(97, 1), days=(7, 60)),
    "Hepatitis E": dict(symptoms=["acute_liver_failure", "coma", "stomach_bleeding", "yellowish_skin", "yellowing_of_eyes", "dark_urine",
                                  "high_fever", "joint_pain", "vomiting", "fatigue", "nausea", "loss_of_appetite", "abdominal_pain"],
                        age=(30, 12), female=0.55, temp=(38.4, 0.6), hr=(102, 14), sbp=(104, 16), spo2=(95, 2), days=(3, 21)),
    "Alcoholic hepatitis": dict(symptoms=["history_of_alcohol_consumption", "swelling_of_stomach", "distention_of_abdomen", "fluid_overload",
                                          "yellowish_skin", "abdominal_pain", "vomiting"],
                                age=(48, 10), female=0.2, temp=LOWF, hr=(92, 12), sbp=(118, 14), spo2=(96, 1.5), days=(7, 90)),
    "Tuberculosis": dict(symptoms=["blood_in_sputum", "cough", "weight_loss", "sweating", "mild_fever", "phlegm", "loss_of_appetite",
                                   "chest_pain", "breathlessness", "swelled_lymph_nodes", "fatigue", "chills", "high_fever", "malaise", "vomiting", "yellowing_of_eyes"],
                         age=(38, 15), female=0.4, temp=LOWF, hr=(94, 10), sbp=(114, 12), spo2=(94, 2.5), days=(21, 180)),
    "Common Cold": dict(symptoms=["runny_nose", "continuous_sneezing", "congestion", "throat_irritation", "sinus_pressure", "cough",
                                  "loss_of_smell", "redness_of_eyes", "headache", "chills", "fatigue", "phlegm", "malaise", "muscle_pain",
                                  "high_fever", "swelled_lymph_nodes", "chest_pain"],
                        age=(28, 17), female=0.5, temp=LOWF, hr=(84, 9), sbp=(118, 10), spo2=(98, 1), days=(1, 7)),
    "Pneumonia": dict(symptoms=["rusty_sputum", "breathlessness", "high_fever", "cough", "chest_pain", "fast_heart_rate", "chills",
                                "phlegm", "sweating", "fatigue", "malaise"],
                      age=(55, 20), female=0.45, temp=(39.0, 0.6), hr=(108, 12), sbp=(112, 14), spo2=(91, 3), days=(2, 10)),
    "Dimorphic hemmorhoids(piles)": dict(symptoms=["pain_in_anal_region", "bloody_stool", "pain_during_bowel_movements", "irritation_in_anus", "constipation"],
                                         age=(45, 13), female=0.45, temp=N, hr=(78, 8), sbp=(124, 12), spo2=(98, 1), days=(7, 120)),
    "Heart attack": dict(symptoms=["chest_pain", "sweating", "breathlessness", "vomiting"],
                         age=(60, 11), female=0.3, temp=N, hr=(108, 18), sbp=(140, 28), spo2=(93, 3), days=(0, 1)),
    "Varicose veins": dict(symptoms=["prominent_veins_on_calf", "swollen_blood_vessels", "swollen_legs", "cramps", "bruising", "obesity", "fatigue"],
                           age=(50, 12), female=0.65, temp=N, hr=(76, 8), sbp=(126, 12), spo2=(98, 1), days=(60, 365)),
    "Hypothyroidism": dict(symptoms=["enlarged_thyroid", "weight_gain", "puffy_face_and_eyes", "cold_hands_and_feets", "brittle_nails", "lethargy",
                                     "fatigue", "mood_swings", "dizziness", "swollen_extremeties", "depression", "irritability", "abnormal_menstruation"],
                           age=(45, 13), female=0.8, temp=(36.6, 0.3), hr=(60, 7), sbp=(126, 12), spo2=(97, 1), days=(60, 365)),
    "Hyperthyroidism": dict(symptoms=["fast_heart_rate", "weight_loss", "sweating", "restlessness", "excessive_hunger", "muscle_weakness",
                                      "fatigue", "mood_swings", "diarrhoea", "irritability", "abnormal_menstruation"],
                            age=(38, 12), female=0.8, temp=(37.4, 0.3), hr=(112, 12), sbp=(134, 12), spo2=(98, 1), days=(30, 180)),
    "Hypoglycemia": dict(symptoms=["sweating", "palpitations", "drying_and_tingling_lips", "slurred_speech", "anxiety", "blurred_and_distorted_vision",
                                   "excessive_hunger", "irritability", "vomiting", "fatigue", "headache", "nausea"],
                         age=(45, 18), female=0.5, temp=N, hr=(104, 12), sbp=(118, 14), spo2=(98, 1), days=(0, 1)),
    "Osteoarthristis": dict(symptoms=["knee_pain", "hip_joint_pain", "joint_pain", "painful_walking", "swelling_joints", "neck_pain"],
                            age=(63, 9), female=0.6, temp=N, hr=(76, 8), sbp=(132, 14), spo2=(97, 1), days=(60, 365)),
    "Arthritis": dict(symptoms=["swelling_joints", "movement_stiffness", "muscle_weakness", "stiff_neck", "painful_walking"],
                      age=(48, 13), female=0.65, temp=(37.2, 0.4), hr=(80, 8), sbp=(126, 12), spo2=(98, 1), days=(30, 365)),
    "(vertigo) Paroymsal  Positional Vertigo": dict(symptoms=["spinning_movements", "loss_of_balance", "unsteadiness", "nausea", "vomiting", "headache"],
                                                    age=(52, 14), female=0.62, temp=N, hr=(80, 8), sbp=(126, 12), spo2=(98, 1), days=(1, 30)),
    "Acne": dict(symptoms=["pus_filled_pimples", "blackheads", "scurring", "skin_rash"],
                 age=(18, 5), female=0.55, temp=N, hr=(76, 8), sbp=(116, 10), spo2=(98, 1), days=(30, 365)),
    "Urinary tract infection": dict(symptoms=["burning_micturition", "continuous_feel_of_urine", "foul_smell_of_urine", "bladder_discomfort"],
                                    age=(36, 16), female=0.82, temp=LOWF, hr=(86, 10), sbp=(118, 12), spo2=(98, 1), days=(1, 7)),
    "Psoriasis": dict(symptoms=["silver_like_dusting", "skin_peeling", "small_dents_in_nails", "inflammatory_nails", "skin_rash", "joint_pain"],
                      age=(38, 14), female=0.5, temp=N, hr=(78, 8), sbp=(122, 12), spo2=(98, 1), days=(30, 365)),
    "Impetigo": dict(symptoms=["red_sore_around_nose", "yellow_crust_ooze", "blister", "skin_rash", "high_fever"],
                     age=(8, 6), female=0.5, temp=LOWF, hr=(96, 12), sbp=(108, 10), spo2=(98, 1), days=(1, 10)),
}

# ------------------------------------------------------- clinical form fields
SYMPTOM_INDEX = {s: i for i, s in enumerate(SYMPTOMS_131)}
CLASS_INDEX = {d: i for i, d in enumerate(DISEASES_41)}

# (name, normal_default, center, scale, label, unit) - vitals are used by triage,
# red flags and the reasoning report (the D1 disease model uses symptoms only)
CLINICAL_FIELDS = [
    ("age", 35.0, 40.0, 20.0, "Age", "years"),
    ("gender_female", 0.5, 0.5, 0.5, "Female", "0/1"),
    ("temperature", 37.0, 37.0, 1.0, "Body temperature", "°C"),
    ("heart_rate", 80.0, 80.0, 15.0, "Heart rate", "bpm"),
    ("systolic_bp", 120.0, 120.0, 20.0, "Systolic BP", "mmHg"),
    ("spo2", 98.0, 97.0, 3.0, "SpO₂", "%"),
    ("duration_days", 7.0, None, None, "Symptom duration", "days"),
]
CLINICAL_NAMES = [f[0] for f in CLINICAL_FIELDS]
CLINICAL_DEFAULTS = {f[0]: f[1] for f in CLINICAL_FIELDS}


def _num(v, default):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def normalize_clinical(clin: dict) -> dict:
    """Fill gaps with normal defaults and clamp to physiologic ranges."""
    c = {}
    c["age"] = min(110.0, max(0.0, _num(clin.get("age"), CLINICAL_DEFAULTS["age"])))
    g = clin.get("gender_female", clin.get("gender"))
    if isinstance(g, str):
        gl = g.strip().lower()
        g = 1.0 if gl in ("f", "female", "woman", "1") else 0.0 if gl in ("m", "male", "man", "0") else 0.5
    c["gender_female"] = _num(g, 0.5)
    c["temperature"] = min(43.0, max(33.0, _num(clin.get("temperature"), 37.0)))
    c["heart_rate"] = min(220.0, max(30.0, _num(clin.get("heart_rate"), 80.0)))
    c["systolic_bp"] = min(260.0, max(60.0, _num(clin.get("systolic_bp"), 120.0)))
    c["spo2"] = min(100.0, max(60.0, _num(clin.get("spo2"), 98.0)))
    c["duration_days"] = min(3650.0, max(0.0, _num(clin.get("duration_days"), 7.0)))
    return c


def _validate_profiles():
    missing = [d for d in DISEASES_41 if d not in DISEASE_PROFILES]
    assert not missing, f"Diseases without profile: {missing}"
    for d, p in DISEASE_PROFILES.items():
        bad = [s for s in p["symptoms"] if s not in SYMPTOM_INDEX]
        assert not bad, f"{d}: unknown symptoms {bad}"


_validate_profiles()


# ----------------------------------------------------- full disease metadata
_EXTRA_METADATA = {
    "Fungal infection": ("Dermatology", "Routine", "Superficial fungal (dermatophyte or candida) infection of skin, causing itchy, scaly, discoloured patches.",
                         ["Keep affected area clean and dry", "Use topical antifungal as prescribed", "Avoid sharing towels and clothing", "Wear loose cotton clothing"]),
    "Allergy": ("General Medicine", "Routine", "Immune hypersensitivity to environmental triggers such as pollen, dust or dander causing sneezing and watery eyes.",
                ["Identify and avoid triggers", "Use antihistamines as advised", "Keep windows closed during high pollen", "Seek care if breathing becomes difficult"]),
    "Chronic cholestasis": ("Gastroenterology", "High", "Impaired bile flow from the liver causing itching, jaundice and fat malabsorption.",
                            ["Get liver function tests and ultrasound", "Avoid alcohol and hepatotoxic drugs", "Eat a low-fat diet", "Follow up with a hepatologist"]),
    "Drug Reaction": ("Dermatology", "High", "Adverse immune or toxic reaction to a medication, commonly presenting as rash and itching.",
                      ["Stop the suspected drug only after consulting a doctor", "Seek emergency care if lips/throat swell", "Record the drug name as an allergy", "Use cool compresses for itching"]),
    "Peptic ulcer diseae": ("Gastroenterology", "Routine", "Open sores in the stomach or duodenal lining, often from H. pylori infection or NSAID use.",
                            ["Avoid NSAIDs, alcohol and smoking", "Test for H. pylori", "Take prescribed acid-suppressing therapy", "Seek urgent care for black stools or vomiting blood"]),
    "AIDS": ("Infectious Disease", "High", "Advanced HIV infection with immune suppression, predisposing to opportunistic infections.",
             ["Confirm with HIV testing and counselling", "Start antiretroviral therapy under specialist care", "Practise safe sex", "Screen for opportunistic infections"]),
    "Cervical spondylosis": ("Orthopedics", "Routine", "Age-related degeneration of cervical spine discs and joints causing neck pain and sometimes nerve symptoms.",
                             ["Maintain good neck posture", "Do physiotherapy neck exercises", "Use a supportive pillow", "Seek care for limb weakness or numbness"]),
    "Paralysis (brain hemorrhage)": ("Neurology", "Urgent", "Bleeding within the brain causing sudden weakness of one side, altered consciousness and headache.",
                                     ["Call emergency services immediately", "Note the time symptoms started", "Do not give food, drink or aspirin", "Keep the patient lying with head slightly raised"]),
    "Jaundice": ("Gastroenterology", "High", "Yellowing of skin and eyes due to raised bilirubin from liver, bile duct or blood disorders.",
                 ["Get liver function tests", "Drink plenty of clean fluids", "Avoid alcohol and fatty food", "Rest and follow up for the cause"]),
    "Malaria": ("Infectious Disease", "Urgent", "Mosquito-borne Plasmodium infection causing cyclical high fever, chills and sweating.",
                ["Get a malaria smear or rapid test today", "Take full antimalarial course if positive", "Use mosquito nets and repellents", "Seek urgent care for confusion or jaundice"]),
    "Chicken pox": ("General Medicine", "Routine", "Varicella-zoster virus infection with itchy vesicular rash and mild fever, mostly in children.",
                    ["Isolate until all blisters crust", "Use calamine lotion for itching", "Avoid aspirin in children", "Keep nails short to prevent scratching"]),
    "Dengue": ("Infectious Disease", "Urgent", "Mosquito-borne viral fever with severe body ache, pain behind eyes and risk of low platelets and bleeding.",
               ["Get NS1/IgM and platelet count", "Take paracetamol only (avoid NSAIDs)", "Drink plenty of fluids", "Seek urgent care for bleeding or abdominal pain"]),
    "Typhoid": ("Infectious Disease", "High", "Salmonella Typhi infection causing prolonged stepwise fever, abdominal pain and toxic look.",
                ["Get blood culture/Widal test", "Complete the prescribed antibiotic course", "Drink only boiled or bottled water", "Eat soft, easily digestible food"]),
    "hepatitis A": ("Gastroenterology", "High", "Food- and water-borne viral liver infection causing acute jaundice; usually self-limiting.",
                    ["Rest and stay hydrated", "Avoid alcohol and paracetamol excess", "Practise strict hand hygiene", "Monitor for confusion or bleeding"]),
    "Hepatitis B": ("Gastroenterology", "High", "Blood- and fluid-borne viral liver infection that may become chronic and lead to cirrhosis.",
                    ["Test HBsAg and viral load", "Avoid alcohol", "Vaccinate household contacts", "Follow up with a hepatologist"]),
    "Hepatitis C": ("Gastroenterology", "High", "Blood-borne viral hepatitis, often silent for years, curable with antiviral therapy.",
                    ["Test anti-HCV and HCV RNA", "Avoid alcohol", "Do not share razors or needles", "Discuss direct-acting antivirals with a specialist"]),
    "Hepatitis D": ("Gastroenterology", "High", "Liver infection that only occurs alongside hepatitis B, causing more severe disease.",
                    ["Test for HDV with HBV markers", "Avoid alcohol", "Seek specialist hepatology care", "Monitor liver function regularly"]),
    "Hepatitis E": ("Gastroenterology", "Urgent", "Water-borne viral hepatitis that can cause acute liver failure, especially in pregnancy.",
                    ["Seek urgent evaluation if confused or bleeding", "Drink only safe water", "Rest and maintain hydration", "Avoid hepatotoxic medicines"]),
    "Alcoholic hepatitis": ("Gastroenterology", "Urgent", "Liver inflammation from heavy alcohol use, causing jaundice, abdominal swelling and fluid overload.",
                            ["Stop alcohol completely with medical support", "Get urgent liver assessment", "Follow a nutritious high-protein diet", "Seek care for vomiting blood or confusion"]),
    "Tuberculosis": ("Pulmonology", "High", "Mycobacterium tuberculosis infection, typically with chronic cough, weight loss, night sweats and fever.",
                     ["Get sputum test and chest X-ray", "Complete the full DOTS treatment course", "Cover mouth when coughing; ventilate rooms", "Screen close contacts"]),
    "Common Cold": ("General Medicine", "Routine", "Self-limiting viral upper respiratory infection with runny nose, sneezing and sore throat.",
                    ["Rest and drink warm fluids", "Use steam inhalation or saline drops", "Wash hands frequently", "See a doctor if fever lasts over 3 days"]),
    "Dimorphic hemmorhoids(piles)": ("General Surgery", "Routine", "Swollen veins in the anal canal causing pain, itching and bright red bleeding with stools.",
                                     ["Eat a high-fibre diet and drink water", "Use warm sitz baths", "Avoid straining at stool", "See a doctor for persistent bleeding"]),
    "Varicose veins": ("Vascular Surgery", "Routine", "Enlarged, twisted superficial leg veins from faulty valves, causing aching and swelling.",
                       ["Elevate legs when resting", "Wear compression stockings", "Avoid standing for long periods", "Exercise and maintain healthy weight"]),
    "Hypothyroidism": ("Endocrinology", "Routine", "Underactive thyroid causing fatigue, weight gain, cold intolerance and slowed metabolism.",
                       ["Test TSH and free T4", "Take thyroxine on an empty stomach daily", "Recheck thyroid levels every 6-8 weeks after dose change", "Eat a balanced iodine-adequate diet"]),
    "Hyperthyroidism": ("Endocrinology", "High", "Overactive thyroid causing weight loss, palpitations, heat intolerance and tremor.",
                        ["Test TSH, free T4 and T3", "Avoid excess caffeine and iodine", "Take prescribed antithyroid medication", "Seek care for very fast heartbeat"]),
    "Hypoglycemia": ("Endocrinology", "Urgent", "Abnormally low blood sugar causing sweating, tremor, confusion and, if severe, seizures.",
                     ["Take 15 g fast sugar (juice, glucose) now", "Recheck sugar after 15 minutes", "Eat a proper meal once recovered", "Call emergency if unconscious"]),
    "Osteoarthristis": ("Orthopedics", "Routine", "Degenerative joint disease of cartilage, commonly knees and hips, causing pain on movement.",
                        ["Do low-impact exercise and physiotherapy", "Maintain healthy weight", "Use walking aids if needed", "Take pain relief as advised"]),
    "(vertigo) Paroymsal  Positional Vertigo": ("ENT", "Routine", "Brief spinning episodes triggered by head position changes due to displaced inner ear crystals.",
                                                ["Move slowly when changing position", "Try repositioning (Epley) manoeuvre with a clinician", "Avoid driving during episodes", "Seek care for new weakness or slurred speech"]),
    "Acne": ("Dermatology", "Routine", "Inflammation of hair follicles and oil glands causing pimples, blackheads and possible scarring.",
             ["Wash face twice daily with gentle cleanser", "Do not squeeze pimples", "Use non-comedogenic products", "See a dermatologist for scarring acne"]),
    "Psoriasis": ("Dermatology", "Routine", "Chronic immune skin disease with silvery scaly plaques, nail changes and sometimes joint pain.",
                  ["Moisturise skin regularly", "Use prescribed topical treatments", "Avoid skin injury and stress triggers", "Report joint pain to your doctor"]),
    "Impetigo": ("Dermatology", "Routine", "Contagious bacterial skin infection with honey-coloured crusted sores, common in children.",
                 ["Gently clean sores and apply prescribed antibiotic", "Keep child home until non-infectious", "Do not share towels", "Wash hands after touching sores"]),
}


def full_disease_metadata() -> Dict[str, dict]:
    from app.ml.disease_kb import DISEASE_METADATA
    out = {}
    for d in DISEASES_41:
        if d in DISEASE_METADATA:
            m = dict(DISEASE_METADATA[d])
        else:
            dept, urg, desc, prec = _EXTRA_METADATA.get(
                d, ("General Medicine", "Routine", "Consult a physician for full evaluation.", ["Consult a physician"]))
            m = {"department": dept, "urgency": urg, "description": desc, "precautions": prec}
        m["typical_symptoms"] = DISEASE_PROFILES[d]["symptoms"]
        out[d] = m
    return out
