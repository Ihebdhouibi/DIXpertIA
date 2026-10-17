from sqlalchemy import BigInteger, Column, DateTime, String, text

from app.core.database import Base


class AuthAttempt(Base):
    """One attempt that counts against a limit (#175).

    Never read or written by the application directly: auth_throttle_hit(),
    auth_throttle_forget() and auth_throttle_clear() do it, as SECURITY DEFINER
    functions, and the application role has no grant on the table. Declared
    here so the models describe the whole schema.
    """

    __tablename__ = "auth_attempts"

    id = Column(BigInteger, primary_key=True)
    bucket = Column(String(20), nullable=False)
    key_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
