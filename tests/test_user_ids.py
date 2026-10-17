"""User ids come from the database, not from a row count (#85).

POST /api/users used to allocate USR-{count + 1}. Once ids were sparse the
count named a live primary key and the insert failed with a 500, and two
concurrent creations computed the same id. users_id_seq now allocates them.
"""

import pytest
from sqlalchemy import text

# Accounts made here are not in conftest's TRUNCATED_BETWEEN_TESTS (users holds
# the fixture accounts), so they are removed by this domain after each test.
# Not a .test domain: the API's email validation rejects reserved names.
DOMAIN = "ids-test.tn"


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})


def create(client, admin, name):
    return client.post("/api/users", headers=admin["headers"], json={
        "email": f"{name}@{DOMAIN}", "firstName": name, "lastName": "Test",
        "role": "employee",
    })


@pytest.mark.identity("admin")
def test_creating_a_user_succeeds_when_ids_are_sparse(client, identities, database):
    admin = identities["admin"]
    first = create(client, admin, "first")
    second = create(client, admin, "second")
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    # Delete the first: the ids are now sparse, and a row count would name
    # the second user's id again.
    with database.connect() as c:
        c.execute(text("DELETE FROM users WHERE id = :id"), {"id": first.json()["id"]})

    third = create(client, admin, "third")
    assert third.status_code == 201, third.text
    ids = {second.json()["id"], third.json()["id"]}
    assert len(ids) == 2
    # Nor is a deleted id handed out again.
    assert first.json()["id"] not in ids


def test_concurrent_inserts_get_distinct_ids(database):
    """Two open transactions each allocate an id before either commits.

    This is the race a count could not survive: both would have read the same
    count and computed the same id, and the second commit would have failed.
    """
    insert = text(
        'INSERT INTO users (email, "firstName", "lastName", role, "hashedPassword")'
        " VALUES (:em, 'Race', 'Test', 'employee', 'x') RETURNING id")
    # The fixture engine autocommits; these two need real transactions held
    # open across both inserts.
    with database.connect() as a, database.connect() as b:
        a = a.execution_options(isolation_level="READ COMMITTED")
        b = b.execution_options(isolation_level="READ COMMITTED")
        ta, tb = a.begin(), b.begin()
        id_a = a.execute(insert, {"em": f"a@{DOMAIN}"}).scalar_one()
        id_b = b.execute(insert, {"em": f"b@{DOMAIN}"}).scalar_one()
        ta.commit()
        tb.commit()
    assert id_a != id_b
    assert id_a.startswith("USR-") and id_b.startswith("USR-")


def test_ids_past_999_keep_every_digit(database):
    """lpad() alone would truncate 1000 to "100"; next_user_id() must not."""
    with database.connect() as c:
        current = c.execute(text("SELECT last_value, is_called FROM users_id_seq")).one()
        try:
            c.execute(text("SELECT setval('users_id_seq', 999, true)"))
            assert c.execute(text("SELECT next_user_id()")).scalar_one() == "USR-1000"
            c.execute(text("SELECT setval('users_id_seq', 6, true)"))
            assert c.execute(text("SELECT next_user_id()")).scalar_one() == "USR-007"
        finally:
            c.execute(text("SELECT setval('users_id_seq', :v, :called)"),
                      {"v": current.last_value, "called": current.is_called})
