from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text, text

from app.core.database import Base


class UserMfa(Base):
    """An account's second factor (#44).

    Never read or written by the application directly: the auth_mfa_*()
    SECURITY DEFINER functions do it, and the application role has no grant on
    the table. `secret_enc` is encrypted by the API with MFA_ENCRYPTION_KEY,
    which never enters the database. Declared so the models describe the
    whole schema.
    """

    __tablename__ = "user_mfa"

    user_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    secret_enc = Column(Text, nullable=False)
    enabled = Column(Boolean, nullable=False, server_default=text("false"))
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    last_step = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class UserMfaRecovery(Base):
    """A single-use recovery code, kept only as an HMAC (#44)."""

    __tablename__ = "user_mfa_recovery"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    code_hash = Column(String(64), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
