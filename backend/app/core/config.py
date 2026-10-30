import os
from pathlib import Path
from typing import Optional, List
from pydantic import model_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = (BASE_DIR / "attendx.db").as_posix()


class Settings(BaseSettings):
    PROJECT_NAME: str = "AttendX AI Smart Attendance"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"

    # Production Cryptographic Security
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # CORS Configuration
    ALLOWED_ORIGINS: str = (
        "null,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080,http://localhost:8765,http://127.0.0.1:8765"
    )
    PRODUCTION_FRONTEND_URL: Optional[str] = None

    # Database URL: supports postgresql, postgresql+asyncpg, or sqlite fallback
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"

    @property
    def sync_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("sqlite:///./"):
            rel_name = url[len("sqlite:///./"):]
            abs_path = (BASE_DIR / rel_name).as_posix()
            return f"sqlite:///{abs_path}"
        return url

    @property
    def cors_origins_list(self) -> List[str]:
        origins = set()
        if self.ALLOWED_ORIGINS:
            for item in self.ALLOWED_ORIGINS.split(","):
                clean = item.strip()
                if clean:
                    origins.add(clean)
        if self.PRODUCTION_FRONTEND_URL:
            for item in self.PRODUCTION_FRONTEND_URL.split(","):
                clean = item.strip()
                if clean:
                    origins.add(clean)
        env_lower = (self.ENVIRONMENT or "development").strip().lower()
        if env_lower not in ("production", "prod"):
            origins.update([
                "null",
                "http://localhost:3000", "http://127.0.0.1:3000",
                "http://localhost:5173", "http://127.0.0.1:5173",
                "http://localhost:5500", "http://127.0.0.1:5500",
                "http://localhost:8000", "http://127.0.0.1:8000",
                "http://localhost:8080", "http://127.0.0.1:8080",
                "http://localhost:8765", "http://127.0.0.1:8765",
            ])
        return sorted(list(origins))

    # AI Verification Thresholds
    FACE_MATCH_SIMILARITY_THRESHOLD: float = 0.75
    LIVENESS_MIN_CONFIDENCE: float = 0.85

    @model_validator(mode="after")
    def validate_security(self):
        env_lower = (self.ENVIRONMENT or "development").strip().lower()
        if env_lower in ("production", "prod"):
            insecure_defaults = [
                "attendx_super_secret_jwt_key_replace_in_production",
                "secret",
                "changeme",
                "change-me",
                "password",
                "default",
            ]
            if not self.SECRET_KEY or not self.SECRET_KEY.strip():
                raise ValueError(
                    "Production security violation: SECRET_KEY environment variable is missing. "
                    "A cryptographically strong random string (at least 32 characters) must be configured in production."
                )
            if self.SECRET_KEY.strip().lower() in insecure_defaults or len(self.SECRET_KEY.strip()) < 32:
                raise ValueError(
                    "Production security violation: The configured SECRET_KEY is insecure or too short (< 32 chars). "
                    "Generate a secure 32+ byte key with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
        else:
            # Safe development/testing fallback if no .env secret provided
            if not self.SECRET_KEY:
                self.SECRET_KEY = "attendx_dev_only_jwt_secret_key_for_local_testing_min32chars"
        return self

    class Config:
        case_sensitive = True
        env_file = [str(BASE_DIR / ".env"), ".env"]
        extra = "allow"


settings = Settings()
