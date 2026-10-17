import os

from dotenv import load_dotenv

# encoding="utf-8-sig" strips a UTF-8 BOM. Without it, an editor-saved .env
# makes the FIRST key parse as "﻿DATABASE_URL", so os.getenv returns None
# and the value is silently ignored. That was the live state of this repo:
# the hard-coded fallback was masking an unreadable .env.
load_dotenv(encoding="utf-8-sig")

# A HS256 signing key shorter than this is brute-forceable offline. The previous
# fallback ("your-secret-key-here") was public in the repository, so any
# deployment that did not set the variable could have its admin tokens forged
# by anyone who had read the source (AUDIT-DB-007).
MIN_SECRET_KEY_LENGTH = 32


class ConfigurationError(RuntimeError):
    """Raised at import time when required configuration is missing or unusable."""


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value or not value.strip():
        raise ConfigurationError(
            f"{name} is not set.\n"
            f"Copy .env.example to .env and set {name}.\n"
            f"There is deliberately no default: a shared fallback value is a "
            f"security hole, not a convenience."
        )
    return value.strip()


def _required_secret(name: str) -> str:
    value = _required(name)
    if len(value) < MIN_SECRET_KEY_LENGTH:
        raise ConfigurationError(
            f"{name} must be at least {MIN_SECRET_KEY_LENGTH} characters "
            f"(got {len(value)}).\n"
            f"Generate one with: python -c "
            f"\"import secrets; print(secrets.token_urlsafe(32))\""
        )
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw not in (None, "") else default
    except ValueError:
        raise ConfigurationError(f"{name} must be a whole number (got {raw!r}).") from None
    if value < 1:
        raise ConfigurationError(f"{name} must be at least 1 (got {value}).")
    return value


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    # No fallbacks. Both of these are required and the process will not start
    # without them.
    DATABASE_URL: str = _required("DATABASE_URL")
    SECRET_KEY: str = _required_secret("SECRET_KEY")

    # Schema changes (Alembic) connect as the owner role, which can
    # CREATE and ALTER. The application role deliberately cannot, so that an
    # application flaw cannot reshape the database. Falls back to DATABASE_URL
    # for environments set up before the roles existed.
    SCHEMA_DATABASE_URL: str = os.getenv("SCHEMA_DATABASE_URL") or _required("DATABASE_URL")

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # Optional: email delivery degrades gracefully when unset (send_email logs a
    # warning and returns False), so these keep their defaults.
    SMTP_HOST: str = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "no-reply@dixpertia.com")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Reminders for invoices stuck in the verification flow (#134). Delays are
    # calendar days at a step before its person is reminded, and again every
    # such period while the invoice stays there.
    REMINDERS_ENABLED: bool = _flag("REMINDERS_ENABLED", True)
    REMINDER_INTERVAL_MINUTES: int = _positive_int("REMINDER_INTERVAL_MINUTES", 60)
    REMINDER_DRAFT_DAYS: int = _positive_int("REMINDER_DRAFT_DAYS", 3)
    REMINDER_REVIEW_DAYS: int = _positive_int("REMINDER_REVIEW_DAYS", 2)
    REMINDER_REJECTED_DAYS: int = _positive_int("REMINDER_REJECTED_DAYS", 2)
    REMINDER_APPROVED_DAYS: int = _positive_int("REMINDER_APPROVED_DAYS", 1)


settings = Settings()
