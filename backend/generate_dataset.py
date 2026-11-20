"""
generate_dataset.py – Generate synthetic heart-disease CSV for model training.
Uses Python standard library (csv, random, math) for 100% dependency-free generation.

Columns:
  patient_id, age, gender, blood_pressure, cholesterol, blood_sugar, bmi,
  smoking, family_history, chest_pain_type, ecg_result, heart_disease

Output: backend/data/heart_disease_synthetic.csv
"""
import os
import csv
import math
import random

# Seed for reproducibility
random.seed(42)

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "heart_disease_synthetic.csv")

N_ROWS = 1200

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def generate():
    rows = []
    for i in range(1, N_ROWS + 1):
        pid = f"PAT{i:04d}"
        age = random.randint(25, 85)
        gender = random.choice([0, 1])  # 0: Female, 1: Male
        
        # Clinical correlations
        base_bp = 115 + (age - 25) * 0.4
        bp = round(random.gauss(base_bp, 15), 1)
        bp = max(85.0, min(220.0, bp))
        
        base_chol = 180 + (age - 25) * 0.8
        chol = round(random.gauss(base_chol, 30), 1)
        chol = max(130.0, min(390.0, chol))
        
        base_sugar = 95 + (age - 25) * 0.4
        sugar = round(random.gauss(base_sugar, 25), 1)
        sugar = max(65.0, min(320.0, sugar))
        
        bmi = round(random.gauss(26.5, 4.5), 1)
        bmi = max(15.0, min(48.0, bmi))
        
        smoking = 1 if random.random() < 0.28 else 0
        family_history = 1 if random.random() < 0.33 else 0
        chest_pain = random.choices([0, 1, 2, 3], weights=[0.25, 0.30, 0.25, 0.20])[0]
        ecg = random.choices([0, 1, 2], weights=[0.55, 0.25, 0.20])[0]

        # Logit risk formula
        risk_logit = (
            0.035 * (age - 45) +
            0.012 * (bp - 120) +
            0.006 * (chol - 200) +
            0.005 * (sugar - 100) +
            0.02 * (bmi - 25) +
            0.65 * smoking +
            0.55 * family_history +
            0.35 * chest_pain +
            0.30 * ecg +
            random.gauss(0, 0.3)
        )
        prob = sigmoid(risk_logit - 1.2)
        heart_disease = 1 if prob > 0.50 else 0

        rows.append([
            pid, age, gender, bp, chol, sugar, bmi,
            smoking, family_history, chest_pain, ecg, heart_disease
        ])

    header = [
        "patient_id", "age", "gender", "blood_pressure", "cholesterol",
        "blood_sugar", "bmi", "smoking", "family_history",
        "chest_pain_type", "ecg_result", "heart_disease"
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"[Dataset] Generated {len(rows)} records at {OUTPUT_FILE}")

if __name__ == "__main__":
    generate()
