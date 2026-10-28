from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "AttendX AI Smart Attendance"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "attendx_super_secret_jwt_key_replace_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # Database URL: supports postgresql, postgresql+asyncpg, or sqlite fallback
    DATABASE_URL: str = "sqlite:///./attendx.db"

    # AI Verification Thresholds
    FACE_MATCH_SIMILARITY_THRESHOLD: float = 0.75
    LIVENESS_MIN_CONFIDENCE: float = 0.85

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"


settings = Settings()
