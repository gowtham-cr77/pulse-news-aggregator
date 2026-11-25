"""Authentication API routes: register, login, logout, and current profile."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import AuthResponse, UserLoginRequest, UserOut, UserRegisterRequest
from app.services.user_service import authenticate_user, register_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Create a new reader account."""
    try:
        return register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate an existing user and return a JWT bearer token."""
    try:
        return authenticate_user(db, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout")
def logout() -> dict:
    """Stateless logout endpoint; clients discard their bearer token."""
    return {"status": "logged_out"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the authenticated user's profile."""
    return UserOut.model_validate(current_user)
