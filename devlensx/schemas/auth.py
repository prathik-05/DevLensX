"""
Authentication Pydantic Schemas
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = "Developer"


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str]
    created_at: datetime
