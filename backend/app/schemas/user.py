from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.STUDENT
    roll_number: Optional[str] = None
    avatar_url: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    embedding_vector: Optional[List[float]] = None  # Biometric facial signature (e.g. 128 or 512 dimensions)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    has_biometric_enrolled: bool = False

    class Config:
        from_attributes = True
