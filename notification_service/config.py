"""
AttendX Notification Service — Configuration Loader
Loads Twilio, WhatsApp Cloud API, database, and cron scheduler settings.
"""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    class NotificationSettings(BaseSettings):
        DATABASE_URL: str = "sqlite:///./attendx.db"
        DAILY_CRON_HOUR: int = 17  # 5:00 PM after class hours
        DAILY_CRON_MINUTE: int = 0
        CONSECUTIVE_ABSENCE_DAYS: int = 3
        WHATSAPP_PROVIDER: str = "twilio"
        TWILIO_ACCOUNT_SID: Optional[str] = None
        TWILIO_AUTH_TOKEN: Optional[str] = None
        TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
        META_WHATSAPP_TOKEN: Optional[str] = None
        META_PHONE_NUMBER_ID: Optional[str] = None
        META_TEMPLATE_NAME: str = "attendx_consecutive_absence_alert"

        class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "allow"
except ImportError:
    class NotificationSettings:
        DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./attendx.db")
        DAILY_CRON_HOUR: int = int(os.getenv("DAILY_CRON_HOUR", "17"))
        DAILY_CRON_MINUTE: int = int(os.getenv("DAILY_CRON_MINUTE", "0"))
        CONSECUTIVE_ABSENCE_DAYS: int = int(os.getenv("CONSECUTIVE_ABSENCE_DAYS", "3"))
        WHATSAPP_PROVIDER: str = os.getenv("WHATSAPP_PROVIDER", "twilio")
        TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
        TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        META_WHATSAPP_TOKEN: Optional[str] = os.getenv("META_WHATSAPP_TOKEN")
        META_PHONE_NUMBER_ID: Optional[str] = os.getenv("META_PHONE_NUMBER_ID")
        META_TEMPLATE_NAME: str = os.getenv("META_TEMPLATE_NAME", "attendx_consecutive_absence_alert")


settings = NotificationSettings()
