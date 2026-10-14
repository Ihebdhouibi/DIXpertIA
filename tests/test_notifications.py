"""Server-side notifications (#116): each user sees and handles only their own.

Notifications are written by the server on events (notify()); the API only
reads them and marks them read or dismissed. The ownership rule is held by the
query and, underneath, by row-level security.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.identity("admin")


@pytest.fixture(autouse=True)
def no_notifications(database):
    # Self-contained on purpose: this table is emptied here rather than in
    # conftest's shared list.
    with database.begin() as c:
        c.execute(text("TRUNCATE notifications RESTART IDENTITY"))


def seed(database, user_id, message, read=False, minutes_ago=0, tone="info"):
    with database.begin() as c:
        return c.execute(text(
            "INSERT INTO notifications (user_id, kind, tone, message, link, created_at, read_at)"
            " VALUES (:u, 'test', :t, :m, 'invoices', now() - make_interval(mins => :ago),"
            " CASE WHEN :r THEN now() END) RETURNING id"),
            {"u": user_id, "t": tone, "m": message, "ago": minutes_ago, "r": read}).scalar()


def test_a_user_lists_only_their_own_unread_first(client, identities, database):
    me, other = identities["accountant"], identities["admin"]
    seed(database, me["user_id"], "old, read", read=True, minutes_ago=1)
    seed(database, me["user_id"], "older, unread", minutes_ago=10)
    seed(database, me["user_id"], "newest, unread", minutes_ago=0)
    seed(database, other["user_id"], "someone else's")

    response = client.get("/api/notifications", headers=me["headers"])
    assert response.status_code == 200
    assert [n["message"] for n in response.json()] == ["newest, unread", "older, unread", "old, read"]
    assert response.headers["X-Unread-Count"] == "2"
    assert response.headers["X-Total-Count"] == "3"


def test_marking_read_and_read_all(client, identities, database):
    me = identities["accountant"]
    first = seed(database, me["user_id"], "one")
    seed(database, me["user_id"], "two")
    read = client.post(f"/api/notifications/{first}/read", headers=me["headers"])
    assert read.status_code == 200 and read.json()["read"] is True
    assert client.post("/api/notifications/read-all", headers=me["headers"]).json() == {"updated": 1}
    listed = client.get("/api/notifications", headers=me["headers"])
    assert listed.headers["X-Unread-Count"] == "0"


def test_someone_elses_notification_is_not_found(client, identities, database):
    """Not 403: a notification of another user is not even revealed to exist."""
    theirs = seed(database, identities["admin"]["user_id"], "for the admin")
    accountant = identities["accountant"]["headers"]
    assert client.post(f"/api/notifications/{theirs}/read", headers=accountant).status_code == 404
    assert client.post(f"/api/notifications/{theirs}/dismiss", headers=accountant).status_code == 404
    with database.connect() as c:
        read_at = c.execute(text("SELECT read_at FROM notifications WHERE id = :i"), {"i": theirs}).scalar()
    assert read_at is None


def test_read_all_leaves_other_users_alone(client, identities, database):
    seed(database, identities["admin"]["user_id"], "for the admin")
    client.post("/api/notifications/read-all", headers=identities["accountant"]["headers"])
    with database.connect() as c:
        unread = c.execute(text("SELECT count(*) FROM notifications WHERE read_at IS NULL")).scalar()
    assert unread == 1


def test_dismissing_is_soft_and_hides_it(client, identities, database):
    me = identities["accountant"]
    one = seed(database, me["user_id"], "one")
    seed(database, me["user_id"], "two")
    assert client.post(f"/api/notifications/{one}/dismiss", headers=me["headers"]).status_code == 204
    assert [n["message"] for n in client.get("/api/notifications", headers=me["headers"]).json()] == ["two"]
    assert client.post("/api/notifications/dismiss-all", headers=me["headers"]).json() == {"dismissed": 1}
    assert client.get("/api/notifications", headers=me["headers"]).json() == []
    with database.connect() as c:
        kept = c.execute(text("SELECT count(*) FROM notifications")).scalar()
    assert kept == 2, "dismissed rows stay, with dismissed_at"


def test_every_role_has_a_notification_list(client, identities):
    for role in ("admin", "accountant", "employee"):
        assert client.get("/api/notifications", headers=identities[role]["headers"]).status_code == 200
    assert client.get("/api/notifications", headers=identities["anonymous"]["headers"]).status_code == 401


def test_the_shape_the_ui_reads(client, identities, database):
    me = identities["accountant"]
    seed(database, me["user_id"], "Invoice BR-0001 is waiting for your verification", tone="warning")
    [n] = client.get("/api/notifications", headers=me["headers"]).json()
    assert n["type"] == "warning" and n["read"] is False and n["link"] == "invoices"
    assert isinstance(n["timestamp"], int) and n["timestamp"] > 0


def test_notify_writes_for_others_in_the_callers_transaction(identities, database):
    """The person acting is rarely the one told: the admin's action notifies the
    accountant. The insert policy allows it; the actor is left out."""
    from app.core.database import SessionLocal
    from app.services.notifications import notify

    with SessionLocal() as db:
        queued = notify(db, [identities["accountant"]["user_id"], identities["admin"]["user_id"]],
                        kind="test", message="hello", exclude=identities["admin"]["user_id"])
        db.commit()
    assert queued == 1
    with database.connect() as c:
        rows = c.execute(text("SELECT user_id FROM notifications")).scalars().all()
    assert rows == [identities["accountant"]["user_id"]]


def test_a_failed_event_notifies_nobody(identities, database):
    from app.core.database import SessionLocal
    from app.services.notifications import notify

    with SessionLocal() as db:
        notify(db, [identities["accountant"]["user_id"]], kind="test", message="never sent")
        db.rollback()
    with database.connect() as c:
        assert c.execute(text("SELECT count(*) FROM notifications")).scalar() == 0
