# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # ===== DATABASE =====
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/dixpertia"

    # ===== SECURITY =====
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ===== CORS =====
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ===== EMAIL (optional) =====
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow extra fields if needed (but we've defined all we use)
        extra = "ignore"   # optional; prevents validation errors on unknown fields

settings = Settings()