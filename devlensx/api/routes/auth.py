"""
DevLensX Authentication API Routes
"""

from fastapi import APIRouter, Depends
from typing import Any
from devlensx.db import get_db, User
from devlensx.schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse
from devlensx.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register(user_in: UserCreate, db: Any = Depends(get_db)):
    """Registers a new developer account and returns an access token."""
    return AuthService.register_user(db, user_in)


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Any = Depends(get_db)):
    """Authenticates developer credentials and returns an access token."""
    return AuthService.login_user(db, credentials)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    db: Any = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Retrieves profile info for the currently authenticated developer."""
    return current_user
