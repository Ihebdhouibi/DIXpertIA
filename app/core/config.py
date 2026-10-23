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


def _minutes(name: str, default: int) -> int:
    # No limit looks back more than a day: auth_throttle_hit() deletes older rows.
    value = _positive_int(name, default)
    if value > 1440:
        raise ConfigurationError(f"{name} must be at most 1440 minutes, one day (got {value}).")
    return value


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _text(name: str, default: str = "") -> str:
    """An optional text setting, trimmed; unset gives the default, set to "" gives ""."""
    raw = os.getenv(name)
    return default if raw is None else raw.strip()


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

    # The public contact form (#98). Every enquiry is stored and notified to the
    # admins; it is also e-mailed to CONTACT_INBOX once that is set, together
    # with SMTP. Empty for now: the professional mailbox is being set up.
    CONTACT_INBOX: str = (os.getenv("CONTACT_INBOX") or "").strip()
    # Anti-abuse: enquiries per sender (by hashed IP) and from everyone, per hour.
    CONTACT_LIMIT_PER_SENDER: int = _positive_int("CONTACT_LIMIT_PER_SENDER", 5)
    CONTACT_LIMIT_TOTAL: int = _positive_int("CONTACT_LIMIT_TOTAL", 100)

    # Brute-force limits (#175), kept in the database (app/services/throttle.py).
    # Failed sign-ins on one e-mail before it is locked, and for how long: the
    # lock lifts as the failures age out of the window.
    LOGIN_MAX_FAILURES: int = _positive_int("LOGIN_MAX_FAILURES", 5)
    LOGIN_LOCKOUT_MINUTES: int = _minutes("LOGIN_LOCKOUT_MINUTES", 15)
    # Failed sign-ins from one address, any account, in the same window.
    LOGIN_MAX_FAILURES_PER_IP: int = _positive_int("LOGIN_MAX_FAILURES_PER_IP", 20)
    # Reset e-mails to one account per hour.
    RESET_MAILS_PER_HOUR: int = _positive_int("RESET_MAILS_PER_HOUR", 3)
    # Requests to the public routes (sign-in, password reset, activation,
    # contact) from one address per minute.
    PUBLIC_REQUESTS_PER_MINUTE: int = _positive_int("PUBLIC_REQUESTS_PER_MINUTE", 20)

    # Two-factor authentication (#44). The key encrypts each account's TOTP
    # secret before it reaches the database, and keys the recovery codes'
    # HMAC: a database dump alone can then mint no code. A Fernet key; keep a
    # copy in the password vault, since losing it means every enrolled account
    # must re-enrol. Empty: two-factor is off, and nobody is asked for it.
    MFA_ENCRYPTION_KEY: str = (os.getenv("MFA_ENCRYPTION_KEY") or "").strip()
    # The roles that must use it: signing in without it leads to enrolment.
    MFA_REQUIRED_ROLES: frozenset = frozenset(
        r.strip() for r in (os.getenv("MFA_REQUIRED_ROLES", "admin,accountant")).split(",") if r.strip())
    # Wrong codes per account before code entry locks, for LOGIN_LOCKOUT_MINUTES.
    MFA_MAX_FAILURES: int = _positive_int("MFA_MAX_FAILURES", 5)

    # /docs, /redoc and /openapi.json (#185). Off by default, so production
    # does not publish a map of every route; on in development and staging.
    API_DOCS: bool = _flag("API_DOCS", False)


    # The seller on every invoice PDF (#194). Empty means not printed: no
    # placeholder ever reaches a real invoice. The tax ID (matricule fiscal),
    # RNE and bank details wait for the company's official details (#189).
    SELLER_NAME: str = _text("SELLER_NAME", "DI Xpertia SUARL")
    SELLER_ADDRESS: str = _text("SELLER_ADDRESS", "Rue de Pasteur, Dar Chaabane El Fehri")
    SELLER_CITY: str = _text("SELLER_CITY", "8011 Nabeul")
    SELLER_PHONE: str = _text("SELLER_PHONE", "+216 28 814 729")
    SELLER_EMAIL: str = _text("SELLER_EMAIL", "contact@dixpertia.com")
    SELLER_TAX_ID: str = _text("SELLER_TAX_ID")
    SELLER_RNE: str = _text("SELLER_RNE")
    SELLER_BANK_NAME: str = _text("SELLER_BANK_NAME")
    SELLER_BANK_HOLDER: str = _text("SELLER_BANK_HOLDER")
    SELLER_RIB: str = _text("SELLER_RIB")
    SELLER_IBAN: str = _text("SELLER_IBAN")
    SELLER_BIC: str = _text("SELLER_BIC")

    # The VAT exemption mention printed on an export invoice (#195), in the
    # client's language. Code de la TVA art. 3-I (a service used abroad is
    # outside its scope) and 11-I (export operations carry a mention).
    EXPORT_MENTION_FR: str = _text(
        "EXPORT_MENTION_FR", "Exportation de services — TVA non applicable (art. 3 et 11 du Code de la TVA)")
    EXPORT_MENTION_EN: str = _text(
        "EXPORT_MENTION_EN", "Export of services — VAT not applicable (art. 3 and 11, Tunisian VAT Code)")


settings = Settings()
