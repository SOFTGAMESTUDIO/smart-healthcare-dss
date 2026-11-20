"""Neural-network AI diagnosis endpoints (FastAPI). Mirrors /api/ai/* in server.py."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.ml.nn_diagnosis_service import get_nn_service

router = APIRouter()


class Clinical(BaseModel):
    age: Optional[float] = None
    gender: Optional[str] = None
    temperature: Optional[float] = None
    heart_rate: Optional[float] = None
    systolic_bp: Optional[float] = None
    spo2: Optional[float] = None
    duration_days: Optional[float] = None


class DiagnoseRequest(BaseModel):
    symptoms: List[str] = Field(..., min_length=1)
    clinical: Clinical = Clinical()
    patient_name: Optional[str] = None
    history_text: str = ""


class FeedbackRequest(BaseModel):
    prediction_id: Optional[int] = None
    confirmed_diagnosis: str
    notes: str = ""
    symptoms: Optional[List[str]] = None
    clinical: Optional[Clinical] = None


class RetrainRequest(BaseModel):
    background: bool = False


class RollbackRequest(BaseModel):
    version: int


@router.get("/schema")
def schema():
    return get_nn_service().schema()


@router.post("/diagnose")
def diagnose(req: DiagnoseRequest) -> Dict[str, Any]:
    res = get_nn_service().diagnose(req.symptoms, req.clinical.model_dump(), patient_name=req.patient_name,
                                    history_text=req.history_text)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@router.post("/feedback")
def feedback(req: FeedbackRequest):
    res = get_nn_service().feedback(req.prediction_id, req.confirmed_diagnosis, req.notes, req.symptoms,
                                    req.clinical.model_dump() if req.clinical else None)
    if not res.get("ok"):
        raise HTTPException(400, res.get("message"))
    return res


@router.post("/retrain")
def retrain(req: RetrainRequest, bg: BackgroundTasks):
    svc = get_nn_service()
    if req.background:
        bg.add_task(svc.retrain, "manual")
        return {"started": True, "message": "Retraining started in background."}
    res = svc.retrain("manual")
    res.pop("entry", None)
    return res


@router.post("/rollback")
def rollback(req: RollbackRequest):
    return get_nn_service().rollback(req.version)


@router.get("/model-info")
def model_info():
    return get_nn_service().model_info()


@router.get("/patterns")
def patterns(disease: Optional[str] = None, top_k: int = Query(8, ge=1, le=12)):
    return get_nn_service().learned_patterns(disease, top_k)


@router.get("/cases")
def cases(limit: int = Query(20, ge=1, le=200)):
    return get_nn_service().recent_cases(limit)
