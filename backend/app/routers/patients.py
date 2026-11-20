"""Patients CRUD + ML prediction + SHAP + Triage."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
from app.database import get_db
from app.models.patient_model import Patient
from app.security import get_current_user, encrypt_field, decrypt_field
import app.ml.disease_model as dm
import app.ml.noshow_model as nm
from app.ml.triage_rules import triage

router = APIRouter()

class PatientCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    age: int
    gender: str
    blood_pressure: float
    cholesterol: float
    blood_sugar: float
    bmi: float
    smoking: int = 0
    family_history: int = 0
    chest_pain_type: int = 0
    ecg_result: int = 0
    symptoms_text: Optional[str] = None

def _serialize_patient(p: Patient) -> dict:
    shap_data = {}
    if p.shap_values_json:
        try:
            shap_data = json.loads(p.shap_values_json)
        except Exception:
            shap_data = {}

    return {
        "id": p.id,
        "name": p.name,
        "phone": p.phone,
        "age": p.age,
        "gender": p.gender,
        "blood_pressure": p.blood_pressure,
        "cholesterol": p.cholesterol,
        "blood_sugar": p.blood_sugar,
        "bmi": p.bmi,
        "smoking": p.smoking,
        "family_history": p.family_history,
        "chest_pain_type": p.chest_pain_type,
        "ecg_result": p.ecg_result,
        "symptoms_text": p.symptoms_text,
        "disease_predicted": p.disease_predicted,
        "risk_score": p.risk_score,
        "noshow_risk": p.noshow_risk,
        "triage_dept": p.triage_dept,
        "shap_values": shap_data,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }

@router.get("/")
def list_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _=Depends(get_current_user)):
    patients = db.query(Patient).offset(skip).limit(limit).all()
    return [_serialize_patient(p) for p in patients]

@router.post("/", status_code=201)
def create_patient(req: PatientCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    patient = Patient(
        encrypted_name=encrypt_field(req.name),
        encrypted_phone=encrypt_field(req.phone) if req.phone else None,
        age=req.age,
        gender=req.gender,
        blood_pressure=req.blood_pressure,
        cholesterol=req.cholesterol,
        blood_sugar=req.blood_sugar,
        bmi=req.bmi,
        smoking=req.smoking,
        family_history=req.family_history,
        chest_pain_type=req.chest_pain_type,
        ecg_result=req.ecg_result,
        symptoms_text=req.symptoms_text,
        created_by=current_user.get("user_id"),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Run ML prediction + Triage immediately
    _run_prediction(patient, req, db)
    return _serialize_patient(patient)

def _run_prediction(patient: Patient, req: Any, db: Session):
    svc = dm.get_ml_service()
    if svc:
        features = dict(
            age=req.age,
            gender=1 if req.gender == "M" else 0,
            blood_pressure=req.blood_pressure,
            cholesterol=req.cholesterol,
            blood_sugar=req.blood_sugar,
            bmi=req.bmi,
            smoking=req.smoking,
            family_history=req.family_history,
            chest_pain_type=req.chest_pain_type,
            ecg_result=req.ecg_result,
        )
        result = svc.predict(features)
        patient.disease_predicted = result["disease_predicted"]
        patient.risk_score = result["risk_score"]
        patient.shap_values_json = json.dumps(result["shap_values"])

        # No-show risk
        ns_svc = nm.get_noshow_service()
        if ns_svc:
            patient.noshow_risk = ns_svc.predict_noshow(
                age=req.age, bmi=req.bmi, distance_km=5.0,
                prev_noshow_count=0, days_until_appt=3,
                risk_score=result["risk_score"]
            )
    else:
        # Fallback heuristic calculation if ML model is training
        risk = min(0.95, max(0.05, 0.01 * req.age + 0.003 * req.blood_pressure + 0.15 * req.smoking))
        patient.risk_score = round(risk, 3)
        patient.disease_predicted = 1 if risk > 0.5 else 0
        patient.noshow_risk = "High" if risk > 0.7 else "Medium" if risk > 0.4 else "Low"

    # Triage engine
    vitals = dict(
        blood_pressure=req.blood_pressure,
        blood_sugar=req.blood_sugar,
        bmi=req.bmi,
        chest_pain_type=req.chest_pain_type,
        ecg_result=req.ecg_result
    )
    triage_result = triage(req.symptoms_text or "", vitals)
    patient.triage_dept = triage_result["department"]

    db.add(patient)
    db.commit()

@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return _serialize_patient(p)

@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(p)
    db.commit()

@router.post("/{patient_id}/predict")
def predict_patient(patient_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    class FakeReq:
        pass
    req = FakeReq()
    req.age = p.age; req.gender = p.gender
    req.blood_pressure = p.blood_pressure; req.cholesterol = p.cholesterol
    req.blood_sugar = p.blood_sugar; req.bmi = p.bmi
    req.smoking = p.smoking; req.family_history = p.family_history
    req.chest_pain_type = p.chest_pain_type; req.ecg_result = p.ecg_result
    req.symptoms_text = p.symptoms_text; req.phone = None
    _run_prediction(p, req, db)
    
    return _serialize_patient(p)
