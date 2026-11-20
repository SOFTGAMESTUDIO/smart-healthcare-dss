"""Appointments router with OR-Tools scheduling."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db
from app.models.appointment_model import Appointment, Doctor
from app.security import get_current_user
from app.scheduler.optimizer import scheduler

router = APIRouter()

class ScheduleRequest(BaseModel):
    patient_ids: List[int]
    scheduling_date: Optional[str] = None

class AppointmentPatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

@router.get("/")
def list_appointments(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _=Depends(get_current_user)):
    appts = db.query(Appointment).offset(skip).limit(limit).all()
    result = []
    for a in appts:
        doc = db.query(Doctor).filter(Doctor.id == a.doctor_id).first()
        result.append({
            "id": a.id, "patient_id": a.patient_id, "doctor_id": a.doctor_id,
            "doctor_name": doc.name if doc else "Unknown",
            "doctor_specialization": doc.specialization if doc else "",
            "slot_datetime": a.slot_datetime.isoformat() if a.slot_datetime else None,
            "duration_minutes": a.duration_minutes,
            "priority_score": a.priority_score,
            "status": a.status, "department": a.department, "notes": a.notes,
        })
    return result

@router.post("/schedule")
def schedule_appointments(req: ScheduleRequest, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from app.models.patient_model import Patient
    
    patients = db.query(Patient).filter(Patient.id.in_(req.patient_ids)).all()
    if not patients:
        raise HTTPException(status_code=404, detail="No patients found")

    requests = [{
        "patient_id": p.id,
        "risk_score": p.risk_score or 0.5,
        "dept": p.triage_dept or "General Medicine",
        "preferred_doctor_id": None,
    } for p in patients]

    doctors = db.query(Doctor).all()
    if not doctors:
        raise HTTPException(status_code=400, detail="No doctors available")

    doctors_data = [{
        "id": d.id, "name": d.name, "specialization": d.specialization,
        "hours_start": d.available_hours_start, "hours_end": d.available_hours_end,
    } for d in doctors]

    existing = db.query(Appointment).filter(Appointment.status == "scheduled").all()
    existing_data = [{"doctor_id": a.doctor_id, "slot_datetime": a.slot_datetime} for a in existing]

    sched_date = None
    if req.scheduling_date:
        sched_date = datetime.fromisoformat(req.scheduling_date)

    assignments = scheduler.schedule(requests, doctors_data, existing_data, sched_date)

    created = []
    for assignment in assignments:
        appt = Appointment(
            patient_id=assignment["patient_id"],
            doctor_id=assignment["doctor_id"],
            slot_datetime=datetime.fromisoformat(assignment["slot_datetime"]),
            priority_score=assignment["priority_score"],
            status="scheduled",
        )
        db.add(appt)
        created.append(assignment)

    db.commit()
    return {"scheduled": len(created), "assignments": created}

@router.patch("/{appointment_id}")
def update_appointment(appointment_id: int, patch: AppointmentPatch, db: Session = Depends(get_db), _=Depends(get_current_user)):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if patch.status:
        appt.status = patch.status
    if patch.notes:
        appt.notes = patch.notes
    db.commit()
    return {"message": "Updated", "appointment_id": appointment_id}

@router.get("/doctors")
def list_doctors(db: Session = Depends(get_db), _=Depends(get_current_user)):
    doctors = db.query(Doctor).all()
    return [{"id": d.id, "name": d.name, "specialization": d.specialization} for d in doctors]
