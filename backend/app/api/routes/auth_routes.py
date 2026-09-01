from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import User, UserRole
from app.auth.security import verify_password, get_password_hash, create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: Optional[UserRole] = UserRole.PUBLIC
    badge_number: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str

class DemoSwitchRequest(BaseModel):
    role: UserRole

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/register", response_model=TokenResponse)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already registered")
        
    hashed = get_password_hash(req.password)
    user = User(
        email=req.email,
        password_hash=hashed,
        full_name=req.full_name,
        role=req.role or UserRole.PUBLIC,
        badge_number=req.badge_number
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(subject=user.email, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "badge_number": user.badge_number
        }
    }

@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    token = create_access_token(subject=user.email, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "badge_number": user.badge_number
        }
    }

@router.post("/demo-switch", response_model=TokenResponse)
def demo_switch_role(req: DemoSwitchRequest, db: Session = Depends(get_db)):
    """
    Seamless 1-click role switcher for interactive testing of Public, Admin, and Inspector workflows.
    """
    target_email = {
        UserRole.PUBLIC: "citizen@roadguard.ai",
        UserRole.ADMIN: "admin@roadguard.ai",
        UserRole.INSPECTOR: "inspector@roadguard.ai"
    }.get(req.role, "citizen@roadguard.ai")
    
    user = db.query(User).filter(User.email == target_email).first()
    if not user:
        # Create demo user on the fly if not exists
        names = {
            UserRole.PUBLIC: "Alex Rivera (Citizen Driver)",
            UserRole.ADMIN: "Elena Vance (Chief City Engineer)",
            UserRole.INSPECTOR: "Marcus Stone (Field Inspector #42)"
        }
        badges = {
            UserRole.PUBLIC: None,
            UserRole.ADMIN: "ADM-9901",
            UserRole.INSPECTOR: "INSP-0042"
        }
        user = User(
            email=target_email,
            password_hash=get_password_hash("roadguard123"),
            full_name=names[req.role],
            role=req.role,
            badge_number=badges[req.role]
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    token = create_access_token(subject=user.email, role=user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "badge_number": user.badge_number
        }
    }

@router.get("/me")
def get_current_user_profile(user: Optional[User] = Depends(get_current_user)):
    if not user:
        return {"authenticated": False, "role": "PUBLIC"}
    return {
        "authenticated": True,
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "badge_number": user.badge_number
    }
