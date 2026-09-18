"""Seed the `users` table so a fresh database can be logged into.

`POST /api/users` requires an authenticated admin, so the first admin cannot be
created through the API. Run this after `python tables.py` on a new database.

    python seed_users.py                       # import the accounts from db.json
    python seed_users.py --admin a@b.tn        # also create/reset an admin (prompts nothing;
                                               #   password defaults to Admin123!)
    python seed_users.py --admin a@b.tn --password s3cret

Importing from db.json carries the existing bcrypt hashes over, so whatever
passwords those accounts already had continue to work. Existing rows are left
untouched unless --admin names them.
"""

import argparse
import json
import os
from datetime import datetime

import bcrypt

from app.core.database import SessionLocal
from app.models.user import User

DB_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db.json")


def import_from_db_json(db):
    if not os.path.exists(DB_JSON):
        print(f"! {DB_JSON} not found - skipping import")
        return 0

    with open(DB_JSON, "r", encoding="utf-8") as f:
        payload = json.load(f)

    added = 0
    for record in payload.get("users", []):
        if db.query(User).filter(User.id == record["id"]).first():
            print(f"  = {record['email']} (id={record['id']}) already present")
            continue
        if db.query(User).filter(User.email == record["email"]).first():
            print(f"  = {record['email']} already present under a different id")
            continue

        created = record.get("createdAt")
        db.add(User(
            id=record["id"],
            email=record["email"],
            firstName=record.get("firstName", ""),
            lastName=record.get("lastName", ""),
            role=record.get("role", "employee"),
            department=record.get("department"),
            avatarUrl=record.get("avatarUrl"),
            hashedPassword=record["hashedPassword"],
            isActive=record.get("isActive", True),
            isVerified=record.get("isVerified", False),
            createdAt=datetime.fromisoformat(created) if created else datetime.now(),
        ))
        print(f"  + {record['email']} (role={record.get('role')})")
        added += 1
    return added


def upsert_admin(db, email, password, first_name, last_name):
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = db.query(User).filter(User.email == email).first()

    if user:
        user.hashedPassword = hashed
        user.role = "admin"
        user.isActive = True
        print(f"  ~ {email} password reset, role forced to admin (id={user.id})")
        return

    # String primary key in the USR-NNN format the rest of the app expects.
    # Derive it from the highest existing number rather than from a row count:
    # db.json ids are sparse (USR-001, USR-003, USR-005), so a count would collide.
    used = set()
    for (existing_id,) in db.query(User.id).all():
        if existing_id and existing_id.startswith("USR-"):
            suffix = existing_id.split("-", 1)[1]
            if suffix.isdigit():
                used.add(int(suffix))
    next_id = f"USR-{(max(used) + 1) if used else 1:03d}"

    db.add(User(
        id=next_id,
        email=email,
        firstName=first_name,
        lastName=last_name,
        role="admin",
        hashedPassword=hashed,
        isActive=True,
        isVerified=True,
        createdAt=datetime.now(),
    ))
    print(f"  + {email} created as admin (id={next_id})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin", help="email of an admin to create or reset")
    parser.add_argument("--password", default="Admin123!")
    parser.add_argument("--first-name", default="Admin")
    parser.add_argument("--last-name", default="DIXpertIA")
    parser.add_argument("--skip-import", action="store_true",
                        help="do not import accounts from db.json")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if not args.skip_import:
            print("Importing users from db.json:")
            import_from_db_json(db)
            # Commit before the admin step so id allocation below sees these rows.
            db.commit()

        if args.admin:
            print("Admin account:")
            upsert_admin(db, args.admin, args.password, args.first_name, args.last_name)
            db.commit()

        print("\nUsers now in the database:")
        for u in db.query(User).order_by(User.id).all():
            print(f"  {u.id}  {u.email}  role={u.role}  active={u.isActive}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
