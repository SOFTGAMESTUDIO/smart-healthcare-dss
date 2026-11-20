"""
disease_kb.py – D1/D2 Knowledge Base & Symptom Catalog.
Contains:
  1. The 131 clinical symptoms categorized by anatomical system.
  2. The 41 disease classes with clinical descriptions and precautions.
  3. Precomputed prototype profiles for instant zero-cold-start inference.
"""

SYMPTOMS_131 = [
    # Head, Neck & Neurological
    "itching", "skin_rash", "nodal_skin_eruptions", "continuous_sneezing", "shivering",
    "chills", "joint_pain", "stomach_pain", "acidity", "ulcers_on_tongue",
    "muscle_wasting", "vomiting", "burning_micturition", "spotting_urination", "fatigue",
    "weight_gain", "anxiety", "cold_hands_and_feets", "mood_swings", "weight_loss",
    "restlessness", "lethargy", "patches_in_throat", "irregular_sugar_level", "cough",
    "high_fever", "sunken_eyes", "breathlessness", "sweating", "dehydration",
    "indigestion", "headache", "yellowish_skin", "dark_urine", "nausea",
    "loss_of_appetite", "pain_behind_the_eyes", "back_pain", "constipation", "abdominal_pain",
    "diarrhoea", "mild_fever", "yellow_urine", "yellowing_of_eyes", "acute_liver_failure",
    "fluid_overload", "swelling_of_stomach", "swelled_lymph_nodes", "malaise", "blurred_and_distorted_vision",
    "phlegm", "throat_irritation", "redness_of_eyes", "sinus_pressure", "runny_nose",
    "congestion", "chest_pain", "weakness_in_limbs", "fast_heart_rate", "pain_during_bowel_movements",
    "pain_in_anal_region", "bloody_stool", "irritation_in_anus", "neck_pain", "dizziness",
    "cramps", "bruising", "obesity", "swollen_legs", "swollen_blood_vessels",
    "puffy_face_and_eyes", "enlarged_thyroid", "brittle_nails", "swollen_extremeties", "excessive_hunger",
    "extra_marital_contacts", "drying_and_tingling_lips", "slurred_speech", "knee_pain", "hip_joint_pain",
    "muscle_weakness", "stiff_neck", "swelling_joints", "movement_stiffness", "spinning_movements",
    "loss_of_balance", "unsteadiness", "weakness_of_one_body_side", "loss_of_smell", "bladder_discomfort",
    "foul_smell_of_urine", "continuous_feel_of_urine", "passage_of_gases", "internal_itching", "toxic_look_(typhos)",
    "depression", "irritability", "muscle_pain", "altered_sensorium", "red_spots_over_body",
    "belly_pain", "abnormal_menstruation", "dischromic_patches", "watering_from_eyes", "increased_appetite",
    "polyuria", "family_history", "mucoid_sputum", "rusty_sputum", "lack_of_concentration",
    "visual_disturbances", "receiving_blood_transfusion", "receiving_unsterile_injections", "coma", "stomach_bleeding",
    "distention_of_abdomen", "history_of_alcohol_consumption", "blood_in_sputum", "prominent_veins_on_calf", "palpitations",
    "painful_walking", "pus_filled_pimples", "blackheads", "scurring", "skin_peeling",
    "silver_like_dusting", "small_dents_in_nails", "inflammatory_nails", "blister", "red_sore_around_nose",
    "yellow_crust_ooze"
]

SYMPTOM_GROUPS = {
    "Cardiovascular & Respiratory": [
        "breathlessness", "chest_pain", "fast_heart_rate", "palpitations",
        "cough", "phlegm", "throat_irritation", "sinus_pressure", "runny_nose",
        "congestion", "mucoid_sputum", "rusty_sputum", "blood_in_sputum"
    ],
    "Gastrointestinal & Hepatic": [
        "stomach_pain", "acidity", "ulcers_on_tongue", "vomiting", "indigestion",
        "nausea", "loss_of_appetite", "abdominal_pain", "constipation", "diarrhoea",
        "yellowish_skin", "dark_urine", "acute_liver_failure", "fluid_overload",
        "swelling_of_stomach", "pain_during_bowel_movements", "pain_in_anal_region",
        "bloody_stool", "irritation_in_anus", "passage_of_gases", "belly_pain",
        "stomach_bleeding", "distention_of_abdomen"
    ],
    "Neurological & Systemic": [
        "headache", "dizziness", "spinning_movements", "loss_of_balance", "unsteadiness",
        "weakness_in_limbs", "slurred_speech", "altered_sensorium", "lack_of_concentration",
        "visual_disturbances", "blurred_and_distorted_vision", "pain_behind_the_eyes",
        "stiff_neck", "weakness_of_one_body_side", "coma", "fatigue", "high_fever",
        "mild_fever", "chills", "shivering", "sweating", "malaise", "anxiety", "depression"
    ],
    "Musculoskeletal & Joints": [
        "joint_pain", "muscle_wasting", "back_pain", "knee_pain", "hip_joint_pain",
        "muscle_weakness", "swelling_joints", "movement_stiffness", "cramps",
        "painful_walking", "muscle_pain", "swollen_legs", "swollen_extremeties"
    ],
    "Dermatology & Skin": [
        "itching", "skin_rash", "nodal_skin_eruptions", "patches_in_throat",
        "red_spots_over_body", "dischromic_patches", "pus_filled_pimples",
        "blackheads", "scurring", "skin_peeling", "silver_like_dusting",
        "small_dents_in_nails", "inflammatory_nails", "blister",
        "red_sore_around_nose", "yellow_crust_ooze", "bruising"
    ],
    "Endocrine & Renal": [
        "weight_gain", "weight_loss", "cold_hands_and_feets", "mood_swings",
        "irregular_sugar_level", "excessive_hunger", "enlarged_thyroid",
        "brittle_nails", "polyuria", "burning_micturition", "spotting_urination",
        "yellow_urine", "continuous_feel_of_urine", "bladder_discomfort", "foul_smell_of_urine"
    ]
}

DISEASES_41 = [
    "Fungal infection", "Allergy", "GERD", "Chronic cholestasis", "Drug Reaction",
    "Peptic ulcer diseae", "AIDS", "Diabetes", "Gastroenteritis", "Bronchial Asthma",
    "Hypertension", "Migraine", "Cervical spondylosis", "Paralysis (brain hemorrhage)",
    "Jaundice", "Malaria", "Chicken pox", "Dengue", "Typhoid", "hepatitis A",
    "Hepatitis B", "Hepatitis C", "Hepatitis D", "Hepatitis E", "Alcoholic hepatitis",
    "Tuberculosis", "Common Cold", "Pneumonia", "Dimorphic hemmorhoids(piles)",
    "Heart attack", "Varicose veins", "Hypothyroidism", "Hyperthyroidism", "Hypoglycemia",
    "Osteoarthristis", "Arthritis", "(vertigo) Paroymsal  Positional Vertigo", "Acne",
    "Urinary tract infection", "Psoriasis", "Impetigo"
]

DISEASE_METADATA = {
    "Heart attack": {
        "department": "Cardiology",
        "urgency": "Urgent",
        "description": "Acute coronary syndrome resulting in myocardial ischemia and tissue necrosis due to coronary arterial occlusion.",
        "precautions": ["Call emergency services immediately", "Administer chewable aspirin 300mg if indicated", "Maintain calm semi-recumbent posture", "Avoid physical exertion"],
        "primary_symptoms": ["chest_pain", "breathlessness", "sweating", "vomiting"]
    },
    "Hypertension": {
        "department": "Cardiology",
        "urgency": "High",
        "description": "Chronically elevated arterial systemic blood pressure exceeding 140/90 mmHg, presenting risks of stroke and cardiovascular disease.",
        "precautions": ["Monitor BP daily morning and evening", "Reduce sodium intake below 2g/day", "Engage in regular aerobic exercise", "Adhere strictly to prescribed antihypertensives"],
        "primary_symptoms": ["headache", "dizziness", "loss_of_balance", "lack_of_concentration"]
    },
    "Bronchial Asthma": {
        "department": "Pulmonology",
        "urgency": "High",
        "description": "Chronic inflammatory disorder of the airways causing hyperresponsiveness, mucosal edema, and reversible bronchoconstriction.",
        "precautions": ["Carry rescue bronchodilator inhaler at all times", "Identify and avoid allergen and smoke triggers", "Use peak flow meter to monitor FEV1", "Keep indoor air humidified and clean"],
        "primary_symptoms": ["breathlessness", "cough", "high_fever", "phlegm"]
    },
    "Pneumonia": {
        "department": "Pulmonology",
        "urgency": "Urgent",
        "description": "Infection that inflames air sacs in one or both lungs, which may fill with fluid or purulent material.",
        "precautions": ["Seek prompt clinical assessment and sputum culture", "Complete full antibiotic regimen if prescribed", "Ensure adequate oral hydration and bed rest", "Monitor pulse oximetry for hypoxemia"],
        "primary_symptoms": ["chills", "high_fever", "breathlessness", "phlegm", "chest_pain", "rusty_sputum"]
    },
    "Diabetes": {
        "department": "Endocrinology",
        "urgency": "Routine",
        "description": "Metabolic disorder characterized by persistent hyperglycemia due to defects in insulin secretion, insulin action, or both.",
        "precautions": ["Monitor fasting and postprandial glucose regularly", "Follow consistent low-glycemic Mediterranean meal plan", "Maintain active physical routine", "Undergo routine diabetic foot and retinal exams"],
        "primary_symptoms": ["fatigue", "weight_loss", "restlessness", "lethargy", "irregular_sugar_level", "increased_appetite", "polyuria"]
    },
    "GERD": {
        "department": "Gastroenterology",
        "urgency": "Routine",
        "description": "Gastroesophageal reflux disease occurring when stomach acid repeatedly flows back into the esophagus, irritating the lining.",
        "precautions": ["Avoid lying down within 3 hours after meals", "Elevate head of bed 6 inches", "Refrain from acidic, spicy, and fatty trigger foods", "Take proton pump inhibitors as directed"],
        "primary_symptoms": ["stomach_pain", "acidity", "ulcers_on_tongue", "vomiting", "cough", "chest_pain"]
    },
    "Migraine": {
        "department": "Neurology",
        "urgency": "Routine",
        "description": "Neurological condition characterized by intense, throbbing unilateral headache accompanied by photophobia, phonophobia, and nausea.",
        "precautions": ["Rest in a dark and quiet environment during episodes", "Maintain consistent sleep and hydration schedules", "Identify dietary triggers like aged cheese and caffeine", "Take prescribed triptans at aura onset"],
        "primary_symptoms": ["headache", "acidity", "indigestion", "visual_disturbances", "blurred_and_distorted_vision", "stiff_neck", "depression"]
    },
    "Gastroenteritis": {
        "department": "Gastroenterology",
        "urgency": "High",
        "description": "Inflammation of the gastrointestinal tract involving stomach and small intestine, resulting in acute diarrhea and dehydration.",
        "precautions": ["Replenish electrolytes using oral rehydration solutions (ORS)", "Follow bland BRAT diet (bananas, rice, applesauce, toast)", "Avoid dairy and caffeinated beverages", "Monitor signs of severe dehydration"],
        "primary_symptoms": ["vomiting", "sunken_eyes", "dehydration", "diarrhoea"]
    },
    "Urinary tract infection": {
        "department": "General Medicine",
        "urgency": "Routine",
        "description": "Microbial infection affecting any part of the urinary system, commonly presenting with dysuria, urgency, and pelvic discomfort.",
        "precautions": ["Increase daily fluid intake to flush urinary tract", "Complete complete course of prescribed antimicrobials", "Avoid caffeinated and alcoholic bladder irritants", "Maintain proper urogenital hygiene"],
        "primary_symptoms": ["burning_micturition", "bladder_discomfort", "foul_smell_of_urine", "continuous_feel_of_urine"]
    },
    "Arthritis": {
        "department": "Orthopedics",
        "urgency": "Routine",
        "description": "Chronic inflammation of one or more joints, leading to progressive cartilage degradation, pain, and restricted mobility.",
        "precautions": ["Engage in low-impact physical therapies (swimming, cycling)", "Apply hot or cold compresses during flare-ups", "Maintain healthy weight to relieve joint stress", "Take NSAIDs or disease-modifying agents as advised"],
        "primary_symptoms": ["muscle_weakness", "stiff_neck", "swelling_joints", "movement_stiffness", "painful_walking"]
    }
}
