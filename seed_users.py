"""Create the first administrator account.

POST /api/users requires an authenticated admin, so the first one cannot be
created through the API. Run this once after `alembic upgrade head`:

    python seed_users.py --email admin@dixpertia.tn
    python seed_users.py --email admin@dixpertia.tn --password 'chosen-password'

With no --password a strong one is generated and printed once. It is shown on
stdout only, never written to a file.

This script deliberately does NOT import accounts from db.json. That file held
bcrypt hashes of three real people plus a live password-reset token, and copying
them into every new database spread real credentials across environments
(AUDIT-DB-007). Accounts come from arguments only.
"""

import argparse
import secrets
import string
import sys
from datetime import datetime

import bcrypt

from app.core.database import SessionLocal
from app.models.user import User

MIN_PASSWORD_LENGTH = 12
ROLES = ("admin", "employee", "accountant")


def generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="omit to generate a strong one")
    parser.add_argument("--first-name", default="Admin")
    parser.add_argument("--last-name", default="DIXpertIA")
    parser.add_argument("--role", default="admin", choices=ROLES)
    args = parser.parse_args()

    password = args.password or generate_password()
    generated = args.password is None
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing:
            existing.hashedPassword = hashed
            existing.role = args.role
            existing.isActive = True
            user_id, action = existing.id, "updated (password reset)"
        else:
            # No id: the database allocates it from users_id_seq (#85). An id
            # chosen here would not advance the sequence, and the next
            # POST /api/users would collide with it.
            user = User(
                email=args.email,
                firstName=args.first_name,
                lastName=args.last_name,
                role=args.role,
                hashedPassword=hashed,
                isActive=True,
                isVerified=True,
                createdAt=datetime.now(),
            )
            db.add(user)
            db.flush()
            user_id, action = user.id, "created"
        db.commit()
    finally:
        db.close()

    print(f"{action}: {args.email}  id={user_id}  role={args.role}")
    if generated:
        print(f"Generated password (shown once): {password}")


if __name__ == "__main__":
    main()
