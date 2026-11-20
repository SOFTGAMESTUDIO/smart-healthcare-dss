"""Authentication router — register, login, me."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.user_model import User
from app.security import verify_password, get_password_hash, create_access_token, get_current_user
from datetime import timedelta
from app.config import settings

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "patient"

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == req.username) | (User.email == req.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already registered")
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=get_password_hash(req.password),
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered successfully", "user_id": user.id}

@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return TokenResponse(access_token=token, token_type="bearer", role=user.role, username=user.username)

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user
