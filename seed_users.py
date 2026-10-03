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


def next_user_id(db) -> str:
    """Allocate USR-NNN from the highest existing number.

    Not from a row count: ids are sparse once anything is deleted, and a count
    then collides with a live primary key. That is the open bug in main.py's
    create_user (#59) which makes POST /api/users fail with a 500.
    """
    used = set()
    for (existing,) in db.query(User.id).all():
        if existing and existing.startswith("USR-"):
            suffix = existing.split("-", 1)[1]
            if suffix.isdigit():
                used.add(int(suffix))
    return f"USR-{(max(used) + 1) if used else 1:03d}"


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
            user_id = next_user_id(db)
            db.add(User(
                id=user_id,
                email=args.email,
                firstName=args.first_name,
                lastName=args.last_name,
                role=args.role,
                hashedPassword=hashed,
                isActive=True,
                isVerified=True,
                createdAt=datetime.now(),
            ))
            action = "created"
        db.commit()
    finally:
        db.close()

    print(f"{action}: {args.email}  id={user_id}  role={args.role}")
    if generated:
        print(f"Generated password (shown once): {password}")


if __name__ == "__main__":
    main()
