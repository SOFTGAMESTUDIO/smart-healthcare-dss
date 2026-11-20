"""
seed_db.py – Populate the SQLite database with test users, doctors, and patients.
Run from the backend/ directory:
    python seed_db.py
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Ensure backend root is in python path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from app.database import engine, Base, SessionLocal
from app.models.user_model import User
from app.models.patient_model import Patient
from app.models.appointment_model import Doctor, Appointment
from app.security import get_password_hash, encrypt_field

def seed():
    print("[Seed] Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Seed Users
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if not existing_admin:
            users = [
                User(
                    username="admin",
                    email="admin@hospital.org",
                    hashed_password=get_password_hash("admin123"),
                    role="admin",
                ),
                User(
                    username="drpriya",
                    email="priya.sharma@hospital.org",
                    hashed_password=get_password_hash("doctor123"),
                    role="physician",
                ),
                User(
                    username="drarjun",
                    email="arjun.mehta@hospital.org",
                    hashed_password=get_password_hash("doctor123"),
                    role="physician",
                ),
                User(
                    username="nurse1",
                    email="nurse1@hospital.org",
                    hashed_password=get_password_hash("nurse123"),
                    role="patient",
                ),
            ]
            db.add_all(users)
            db.commit()
            print("[Seed] Created 4 users (admin, drpriya, drarjun, nurse1).")
        else:
            print("[Seed] Users already present, skipping.")

        # 2. Seed Doctors
        existing_doc = db.query(Doctor).first()
        if not existing_doc:
            doctors = [
                Doctor(name="Dr. Priya Sharma", specialization="Cardiology", available_hours_start=9, available_hours_end=17),
                Doctor(name="Dr. Arjun Mehta", specialization="General Medicine", available_hours_start=9, available_hours_end=17),
                Doctor(name="Dr. Kavya Reddy", specialization="Pulmonology", available_hours_start=10, available_hours_end=18),
                Doctor(name="Dr. Rahul Singh", specialization="Endocrinology", available_hours_start=9, available_hours_end=15),
                Doctor(name="Dr. Ananya Iyer", specialization="Neurology", available_hours_start=11, available_hours_end=19),
            ]
            db.add_all(doctors)
            db.commit()
            print("[Seed] Created 5 doctors across specialties.")
        else:
            print("[Seed] Doctors already present, skipping.")

        # 3. Seed Patients with Precalculated SHAP values & Clinical Vitals
        existing_patient = db.query(Patient).first()
        if not existing_patient:
            sample_patients = [
                {
                    "name": "Ramesh Kumar",
                    "phone": "+91-9845012345",
                    "age": 68,
                    "gender": "M",
                    "bp": 175.0,
                    "chol": 310.0,
                    "sugar": 240.0,
                    "bmi": 32.4,
                    "smoking": 1,
                    "family_history": 1,
                    "chest_pain": 3,
                    "ecg": 2,
                    "symptoms": "Severe substernal chest pain radiating to left arm, shortness of breath, heavy sweating",
                    "pred": 1,
                    "risk": 0.89,
                    "noshow": "Low",
                    "triage": "Emergency",
                    "shap": {
                        "age": 0.18, "gender": 0.05, "blood_pressure": 0.22,
                        "cholesterol": 0.19, "blood_sugar": 0.14, "bmi": 0.11,
                        "smoking": 0.20, "family_history": 0.15, "chest_pain_type": 0.25,
                        "ecg_result": 0.18
                    }
                },
                {
                    "name": "Sunita Rao",
                    "phone": "+91-9876543210",
                    "age": 59,
                    "gender": "F",
                    "bp": 158.0,
                    "chol": 275.0,
                    "sugar": 185.0,
                    "bmi": 29.1,
                    "smoking": 0,
                    "family_history": 1,
                    "chest_pain": 2,
                    "ecg": 1,
                    "symptoms": "Occasional palpitations, fatigue on moderate exertion, mild dizziness",
                    "pred": 1,
                    "risk": 0.74,
                    "noshow": "Medium",
                    "triage": "Cardiology",
                    "shap": {
                        "age": 0.12, "gender": -0.04, "blood_pressure": 0.16,
                        "cholesterol": 0.14, "blood_sugar": 0.10, "bmi": 0.08,
                        "smoking": -0.05, "family_history": 0.12, "chest_pain_type": 0.14,
                        "ecg_result": 0.09
                    }
                },
                {
                    "name": "Vijay Nair",
                    "phone": "+91-9123456789",
                    "age": 72,
                    "gender": "M",
                    "bp": 185.0,
                    "chol": 330.0,
                    "sugar": 290.0,
                    "bmi": 33.8,
                    "smoking": 1,
                    "family_history": 1,
                    "chest_pain": 3,
                    "ecg": 2,
                    "symptoms": "Acute retrosternal crushing pain, diaphoresis, hypertension emergency",
                    "pred": 1,
                    "risk": 0.94,
                    "noshow": "Low",
                    "triage": "Emergency",
                    "shap": {
                        "age": 0.21, "gender": 0.06, "blood_pressure": 0.26,
                        "cholesterol": 0.22, "blood_sugar": 0.18, "bmi": 0.14,
                        "smoking": 0.22, "family_history": 0.17, "chest_pain_type": 0.28,
                        "ecg_result": 0.20
                    }
                },
                {
                    "name": "Ananya Sen",
                    "phone": "+91-9988776655",
                    "age": 34,
                    "gender": "F",
                    "bp": 115.0,
                    "chol": 170.0,
                    "sugar": 88.0,
                    "bmi": 21.5,
                    "smoking": 0,
                    "family_history": 0,
                    "chest_pain": 0,
                    "ecg": 0,
                    "symptoms": "Mild persistent dry cough, seasonal allergy symptoms, nasal congestion",
                    "pred": 0,
                    "risk": 0.12,
                    "noshow": "Low",
                    "triage": "Pulmonology",
                    "shap": {
                        "age": -0.15, "gender": -0.05, "blood_pressure": -0.12,
                        "cholesterol": -0.10, "blood_sugar": -0.08, "bmi": -0.09,
                        "smoking": -0.07, "family_history": -0.06, "chest_pain_type": -0.11,
                        "ecg_result": -0.08
                    }
                },
                {
                    "name": "Deepa Menon",
                    "phone": "+91-9445566778",
                    "age": 45,
                    "gender": "F",
                    "bp": 136.0,
                    "chol": 218.0,
                    "sugar": 124.0,
                    "bmi": 26.2,
                    "smoking": 0,
                    "family_history": 1,
                    "chest_pain": 1,
                    "ecg": 0,
                    "symptoms": "Mild breathlessness when climbing stairs, slight fatigue, occasional headache",
                    "pred": 0,
                    "risk": 0.48,
                    "noshow": "Medium",
                    "triage": "General Medicine",
                    "shap": {
                        "age": 0.02, "gender": -0.03, "blood_pressure": 0.07,
                        "cholesterol": 0.05, "blood_sugar": 0.04, "bmi": 0.03,
                        "smoking": -0.05, "family_history": 0.09, "chest_pain_type": 0.05,
                        "ecg_result": -0.02
                    }
                },
                {
                    "name": "Suresh Babu",
                    "phone": "+91-9334455667",
                    "age": 52,
                    "gender": "M",
                    "bp": 148.0,
                    "chol": 242.0,
                    "sugar": 145.0,
                    "bmi": 28.3,
                    "smoking": 1,
                    "family_history": 0,
                    "chest_pain": 1,
                    "ecg": 1,
                    "symptoms": "Chest tightness on brisk walking, tingling sensation in left fingertips",
                    "pred": 1,
                    "risk": 0.62,
                    "noshow": "Low",
                    "triage": "Cardiology",
                    "shap": {
                        "age": 0.08, "gender": 0.04, "blood_pressure": 0.11,
                        "cholesterol": 0.09, "blood_sugar": 0.07, "bmi": 0.06,
                        "smoking": 0.16, "family_history": -0.04, "chest_pain_type": 0.08,
                        "ecg_result": 0.06
                    }
                },
                {
                    "name": "Preethi Seshadri",
                    "phone": "+91-9112233445",
                    "age": 28,
                    "gender": "F",
                    "bp": 110.0,
                    "chol": 165.0,
                    "sugar": 82.0,
                    "bmi": 20.8,
                    "smoking": 0,
                    "family_history": 0,
                    "chest_pain": 0,
                    "ecg": 0,
                    "symptoms": "Routine corporate annual health checkup, no current complaints",
                    "pred": 0,
                    "risk": 0.08,
                    "noshow": "Low",
                    "triage": "General Medicine",
                    "shap": {
                        "age": -0.19, "gender": -0.06, "blood_pressure": -0.15,
                        "cholesterol": -0.13, "blood_sugar": -0.10, "bmi": -0.12,
                        "smoking": -0.08, "family_history": -0.07, "chest_pain_type": -0.14,
                        "ecg_result": -0.10
                    }
                },
                {
                    "name": "Karan Malhotra",
                    "phone": "+91-9223344556",
                    "age": 41,
                    "gender": "M",
                    "bp": 128.0,
                    "chol": 205.0,
                    "sugar": 110.0,
                    "bmi": 25.1,
                    "smoking": 1,
                    "family_history": 0,
                    "chest_pain": 0,
                    "ecg": 0,
                    "symptoms": "Acid reflux, epigastric discomfort after spicy meals, bloating",
                    "pred": 0,
                    "risk": 0.32,
                    "noshow": "High",
                    "triage": "Gastroenterology",
                    "shap": {
                        "age": -0.03, "gender": 0.03, "blood_pressure": 0.02,
                        "cholesterol": 0.02, "blood_sugar": 0.01, "bmi": 0.01,
                        "smoking": 0.12, "family_history": -0.05, "chest_pain_type": -0.08,
                        "ecg_result": -0.06
                    }
                },
            ]

            patient_objs = []
            for p in sample_patients:
                patient_objs.append(
                    Patient(
                        encrypted_name=encrypt_field(p["name"]),
                        encrypted_phone=encrypt_field(p["phone"]),
                        age=p["age"],
                        gender=p["gender"],
                        blood_pressure=p["bp"],
                        cholesterol=p["chol"],
                        blood_sugar=p["sugar"],
                        bmi=p["bmi"],
                        smoking=p["smoking"],
                        family_history=p["family_history"],
                        chest_pain_type=p["chest_pain"],
                        ecg_result=p["ecg"],
                        symptoms_text=p["symptoms"],
                        disease_predicted=p["pred"],
                        risk_score=p["risk"],
                        noshow_risk=p["noshow"],
                        triage_dept=p["triage"],
                        shap_values_json=json.dumps(p["shap"]),
                    )
                )
            db.add_all(patient_objs)
            db.commit()
            print(f"[Seed] Created {len(patient_objs)} patients with DPDP encrypted names/phones.")

            # 4. Seed initial appointments
            docs = db.query(Doctor).all()
            patients = db.query(Patient).all()
            now = datetime.now()

            appts = [
                Appointment(
                    patient_id=patients[0].id,
                    doctor_id=docs[0].id,
                    slot_datetime=now + timedelta(hours=2),
                    duration_minutes=30,
                    priority_score=0.89,
                    status="scheduled",
                    department="Cardiology",
                    notes="Urgent evaluation needed",
                ),
                Appointment(
                    patient_id=patients[1].id,
                    doctor_id=docs[0].id,
                    slot_datetime=now + timedelta(days=1, hours=4),
                    duration_minutes=30,
                    priority_score=0.74,
                    status="scheduled",
                    department="Cardiology",
                    notes="Follow-up on palpitations",
                ),
                Appointment(
                    patient_id=patients[4].id,
                    doctor_id=docs[1].id,
                    slot_datetime=now + timedelta(days=2, hours=3),
                    duration_minutes=30,
                    priority_score=0.48,
                    status="scheduled",
                    department="General Medicine",
                    notes="General wellness visit",
                ),
            ]
            db.add_all(appts)
            db.commit()
            print(f"[Seed] Created {len(appts)} initial appointments.")
        else:
            print("[Seed] Patients already present, skipping.")

        print("[Seed] Database seeding completed successfully! ✅")

    except Exception as e:
        db.rollback()
        print(f"[Seed Error] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
