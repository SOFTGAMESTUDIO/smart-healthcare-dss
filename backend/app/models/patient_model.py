from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from app.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    encrypted_name = Column(String(500), nullable=False)
    encrypted_phone = Column(String(500), nullable=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(1), nullable=False)   # M | F
    blood_pressure = Column(Float, nullable=False)
    cholesterol = Column(Float, nullable=False)
    blood_sugar = Column(Float, nullable=False)
    bmi = Column(Float, nullable=False)
    smoking = Column(Integer, default=0)
    family_history = Column(Integer, default=0)
    chest_pain_type = Column(Integer, default=0)  # 0-3
    ecg_result = Column(Integer, default=0)       # 0-2
    symptoms_text = Column(Text, nullable=True)
    
    # ML & Decision Support outputs
    disease_predicted = Column(Integer, nullable=True)
    risk_score = Column(Float, nullable=True)
    noshow_risk = Column(String(10), nullable=True)   # Low | Medium | High
    triage_dept = Column(String(50), nullable=True)
    shap_values_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, nullable=True)

    @property
    def name(self) -> str:
        if not self.encrypted_name:
            return ""
        from app.security import decrypt_field
        return decrypt_field(self.encrypted_name)

    @property
    def phone(self) -> str:
        if not self.encrypted_phone:
            return ""
        from app.security import decrypt_field
        return decrypt_field(self.encrypted_phone)
