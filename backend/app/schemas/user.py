from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, model_validator
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
    email: Optional[str] = Field(None, description="Email address or student roll number")
    username: Optional[str] = Field(None, description="Username, email address, or roll number alias")
    password: str = Field(..., description="Account password")

    @model_validator(mode="before")
    @classmethod
    def validate_identifier(cls, data):
        if isinstance(data, dict):
            identifier = data.get("email") or data.get("username")
            if not identifier or not str(identifier).strip():
                raise ValueError("An email address or student roll number is required.")
            cleaned_identifier = str(identifier).strip()
            data["email"] = cleaned_identifier
            if not data.get("username"):
                data["username"] = cleaned_identifier
        elif hasattr(data, "email") or hasattr(data, "username"):
            identifier = getattr(data, "email", None) or getattr(data, "username", None)
            if not identifier or not str(identifier).strip():
                raise ValueError("An email address or student roll number is required.")
        return data

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "teacher@attendx.ai",
                "password": "Teacher@123"
            }
        }
    }


class UserResponse(UserBase):
    id: int
    created_at: datetime
    has_biometric_enrolled: bool = False

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    name: str
    email: EmailStr
    roll_number: str
    password: Optional[str] = "Student@123"
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_notifications_enabled: Optional[bool] = True


class StudentListItem(BaseModel):
    id: int
    name: str
    email: str
    role: str
    roll_number: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_notifications_enabled: bool = True
    has_biometric_enrolled: bool = False
    session_status: str = "PENDING"
    confidence_score: Optional[float] = None
    distance_meters: Optional[float] = None
    last_verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True

