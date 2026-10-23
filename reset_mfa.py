"""Remove an account's second factor, from the server (#44): the break-glass.

For when nobody who can do it in the app can sign in: the only admin lost
their phone and their recovery codes, or MFA_ENCRYPTION_KEY was lost and no
enrolled account can pass its second step. The admin resets anyone else's from
the Users screen; this is for the rest.

Run inside the API container, which has the schema owner's URL only while
this runs (docker exec gets the container's environment):

    sudo docker exec -it $(sudo docker ps -q -f name=dixpertia-api- | head -1) \\
        python reset_mfa.py --email admin@dixpertia.tn

It removes the account's second factor and signs it out everywhere. At its
next sign-in, a role that requires two-factor enrols again. The reset is
written to the audit trail.
"""

import argparse
import sys

from sqlalchemy import create_engine, text

from app.core.config import settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    # As the schema owner: there is no signed-in admin to do it as, and the
    # application role can reach these tables only through the functions.
    engine = create_engine(settings.SCHEMA_DATABASE_URL)
    with engine.begin() as db:
        user_id = db.execute(text("SELECT id FROM users WHERE email = :e"), {"e": args.email}).scalar()
        if user_id is None:
            print(f"No account for {args.email}.")
            return 1
        removed = db.execute(text("DELETE FROM user_mfa_recovery WHERE user_id = :u"), {"u": user_id}).rowcount
        had = db.execute(text("DELETE FROM user_mfa WHERE user_id = :u"), {"u": user_id}).rowcount
        if not had:
            print(f"{args.email} has no second factor; nothing changed.")
            return 0
        db.execute(text("UPDATE users SET token_version = token_version + 1 WHERE id = :u"), {"u": user_id})
        db.execute(text(
            "INSERT INTO audit_events (actor_id, actor_role, action, entity, entity_id)"
            " VALUES (NULL, 'server', 'user.mfa_reset', 'user', :u)"), {"u": user_id})
    print(f"Second factor removed for {args.email} ({removed} recovery codes), every session signed out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
