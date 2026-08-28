import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Fallback to the working hardcoded URL if the environment variable is missing or contains invalid characters
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/dixpertia")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SMTP_HOST: str = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "no-reply@dixpertia.com")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

settings = Settings()