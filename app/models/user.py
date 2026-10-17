from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, text
from datetime import datetime
from sqlalchemy.orm import deferred, relationship

from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    # The database allocates USR-NNN from users_id_seq (#85). Leave id unset on
    # insert; a row count collided with live ids once they were sparse.
    id = Column(String, primary_key=True, server_default=text("next_user_id()"))
    email = Column(String, unique=True, index=True, nullable=False)
    firstName = Column(String)
    lastName = Column(String)
    role = Column(String, nullable=False)  # "admin", "employee", "accountant"
    department = Column(String, nullable=True)
    avatarUrl = Column(String, nullable=True)
    # Never loaded with the row (#76): the application role holds no SELECT on
    # this column, and raiseload makes an accidental read fail here, by name,
    # rather than as a permission error from PostgreSQL. Sign-in reads it
    # through auth_account_by_email(); writing it (a new account) still works.
    hashedPassword = deferred(Column(String, nullable=False), raiseload=True)
    isActive = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    # False until the owner sets a password through the activation link (#62).
    isVerified = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    createdAt = Column(DateTime, default=datetime.utcnow)
    # Carried in every access token; bumping it revokes them all (#62).
    token_version = Column(Integer, nullable=False, default=0, server_default=text("0"))

    employee = relationship("Employee", back_populates="user", uselist=False)

    __table_args__ = (
        # Roles are a closed set; the audit inserted 'superadmin' cleanly (#58).
        CheckConstraint("role IN ('admin', 'employee', 'accountant')", name="ck_users_role"),
        # Email is an identity, so uniqueness must ignore case: PROBE@x and
        # probe@x were both accepted. UNIQUE(email) cannot express this.
        Index("ux_users_email_ci", text("lower(email)"), unique=True),
    )


class AccountToken(Base):
    """A single-use reset or activation token (#62). Only its SHA-256 is stored.

    Replaces users.resetToken, which held a session-key JWT in clear. A token
    is spent by setting used_at, never deleted.
    """

    __tablename__ = "account_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose = Column(String(20), nullable=False)  # "reset" or "activation"
    token_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("purpose IN ('reset', 'activation')", name="ck_account_tokens_purpose"),
        CheckConstraint("expires_at > created_at", name="ck_account_tokens_expiry"),
        Index("ix_account_tokens_user_live", "user_id", "purpose", postgresql_where=text("used_at IS NULL")),
    )
