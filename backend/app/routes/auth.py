from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models.dependencies import get_db, get_current_user
from app.services.auth_service import AuthService
from app.core.database import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class RegisterResponse(BaseModel):
    message: str
    user: dict


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str


class LogoutResponse(BaseModel):
    message: str


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = AuthService.register_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
        return RegisterResponse(message="User registered successfully", user=user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        result = AuthService.login_user(
            db=db,
            email=request.email,
            password=request.password,
        )
        return LoginResponse(**result)
    except ValueError as e:
        status_code = 403 if "disabled" in str(e).lower() else 401
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    try:
        result = AuthService.refresh_access_token(
            db=db,
            refresh_token=request.refresh_token,
        )
        return RefreshResponse(**result)
    except ValueError as e:
        status_code = 403 if "disabled" in str(e).lower() else 401
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.exception("Token refresh failed")
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        AuthService.logout_user(str(user.id), credentials.credentials)
        return LogoutResponse(message="Logged out successfully")
    except Exception as e:
        logger.exception("Logout failed")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "is_active": user.is_active,
        "role": getattr(user, "role", "user"),
    }


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None


@router.patch("/me")
async def update_me(
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.full_name is not None:
        user.full_name = body.full_name.strip() or None
    db.commit()
    db.refresh(user)
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": getattr(user, "role", "user"),
    }
