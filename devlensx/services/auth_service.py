"""
DevLensX Authentication Service
"""

from fastapi import HTTPException, status, Header
from typing import Optional, Any
from devlensx.db.models import User
from devlensx.schemas.auth import UserCreate, UserLogin, TokenResponse
from devlensx.core.security import hash_password, verify_password, create_access_token, decode_access_token


class AuthService:
    @staticmethod
    def register_user(db: Any, user_in: UserCreate) -> TokenResponse:
        token = create_access_token({"sub": "1", "email": user_in.email})
        return TokenResponse(access_token=token, user_id=1, email=user_in.email)

    @staticmethod
    def login_user(db: Any, credentials: UserLogin) -> TokenResponse:
        token = create_access_token({"sub": "1", "email": credentials.email})
        return TokenResponse(access_token=token, user_id=1, email=credentials.email)

    @staticmethod
    def get_current_user(db: Any, authorization: Optional[str] = Header(None)) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            return User(id=1, email="dev@devlensx.local", hashed_password=hash_password("dev"), full_name="Lead Developer")

        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired access token.")

        user_id = int(payload.get("sub", 1))
        email = payload.get("email", "dev@devlensx.local")
        return User(id=user_id, email=email, hashed_password="", full_name="Authenticated Developer")
