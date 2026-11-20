"""FastAPI application entry point with lifespan ML preloading."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.ml.disease_model as dm
import app.ml.noshow_model as nm
from app.database import init_db
from app.routers import auth, patients, appointments, analytics, ai, research
from app.ml.nn_diagnosis_service import get_nn_service

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Initialize DB
    init_db()
    print("[Startup] Database initialized with WAL mode.")
    
    # Train / load ML models into RAM (warm cache)
    print("[Startup] Loading Disease XGBoost + SHAP explainer...")
    dm.ml_service = dm.DiseaseMLService()
    
    print("[Startup] Loading No-Show model (D3)...")
    nm.get_noshow_service()
    
    print("[Startup] Loading D1 disease MLP + Kernel SHAP...")
    get_nn_service()

    print("[Startup] All ML models loaded. API ready.")
    yield
    print("[Shutdown] Cleaning up...")

app = FastAPI(
    title="XAI Healthcare Decision Support System",
    description="Explainable AI-driven disease prediction, triage, and appointment scheduling",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Diagnosis (D1 MLP + Kernel SHAP)"])
app.include_router(research.router, prefix="/api/research", tags=["Research results"])

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "ml_loaded": dm.ml_service is not None,
        "noshow_loaded": nm.noshow_service is not None,
    }
