"""Demo videos (#232): link recognition, the admin's routes, and the website's read.

No video file is stored: a demo is a link to Drive, YouTube or Vimeo. The
admin manages demos; the website reads the published ones through
published_demos(), never the table.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.identity("admin")

DRIVE = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view?usp=sharing"
DEMO = {
    "title_fr": "Tableau de bord comptable", "title_en": "Accounting dashboard",
    "description_fr": "Le suivi des factures, de la saisie à la clôture du mois.",
    "description_en": "Invoices followed from entry to month close.",
    "video_url": DRIVE,
}


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


def create(client, admin, **changes):
    return client.post("/api/demos", headers=admin, json={**DEMO, **changes})


# --- Link recognition -----------------------------------------------------------------

@pytest.mark.parametrize("url,provider,video_id", [
    (DRIVE, "drive", "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"),
    ("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/preview", "drive", "1AbCdEfGhIjKlMnOp"),
    ("https://drive.google.com/open?id=1AbCdEfGhIjKlMnOp", "drive", "1AbCdEfGhIjKlMnOp"),
    ("https://drive.google.com/uc?export=download&id=1AbCdEfGhIjKlMnOp", "drive", "1AbCdEfGhIjKlMnOp"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "youtube", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "youtube", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "youtube", "dQw4w9WgXcQ"),
    ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "youtube", "dQw4w9WgXcQ"),
    ("https://vimeo.com/76979871", "vimeo", "76979871"),
    ("https://vimeo.com/76979871/8272103f6e", "vimeo", "76979871-8272103f6e"),
    ("https://player.vimeo.com/video/76979871?h=8272103f6e", "vimeo", "76979871-8272103f6e"),
])
def test_a_supported_link_is_recognised(url, provider, video_id):
    from app.services.demo_links import parse_video_link

    assert parse_video_link(url) == (provider, video_id)


@pytest.mark.parametrize("url", [
    "http://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view",       # not https
    "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp",    # a folder, not a file
    "https://www.youtube.com/watch?v=short",                       # malformed id
    "https://www.youtube.com/channel/UCabcdefghijk",               # a channel
    "https://vimeo.com/channels/staffpicks",                       # not a video
    "https://example.com/video.mp4",                               # another host
    "https://drive.google.com.evil.example/file/d/1AbCdEfGhIjKlMnOp/view",
    "javascript:alert(1)",
    "",
])
def test_anything_else_is_not(url):
    from app.services.demo_links import parse_video_link

    assert parse_video_link(url) is None


def test_the_players_and_previews_built_from_a_link():
    from app.services.demo_links import embed_url, preview_image

    assert embed_url("drive", "1AbCdEfGhIjKlMnOp") == "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/preview"
    assert embed_url("youtube", "dQw4w9WgXcQ").startswith("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
    assert embed_url("vimeo", "76979871-8272103f6e") == "https://player.vimeo.com/video/76979871?dnt=1&h=8272103f6e"
    # The admin's image wins; otherwise the platform's own thumbnail; Vimeo has none.
    assert preview_image("drive", "VID12345678", "https://drive.google.com/file/d/IMG12345678/view") \
        == "https://drive.google.com/thumbnail?id=IMG12345678&sz=w1280"
    assert preview_image("drive", "VID12345678", None) == "https://drive.google.com/thumbnail?id=VID12345678&sz=w1280"
    assert preview_image("youtube", "dQw4w9WgXcQ", None) == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    assert preview_image("vimeo", "76979871", None) is None


# --- The admin manages them -----------------------------------------------------------

def test_a_demo_is_created_hidden_and_last(client, admin):
    first = create(client, admin)
    assert first.status_code == 201, first.text
    body = first.json()
    assert (body["provider"], body["published"], body["position"]) == ("drive", False, 0)
    assert body["embed_url"].endswith("/preview")
    assert create(client, admin, title_fr="Deuxième", title_en="Second").json()["position"] == 1


@pytest.mark.parametrize("changes", [
    {"title_fr": "  "},
    {"title_en": "x" * 81},
    {"description_fr": "x" * 301},
    {"service": "marketing"},
])
def test_invalid_content_is_refused(client, admin, changes):
    assert create(client, admin, **changes).status_code == 422


def test_an_unknown_link_is_refused_in_the_callers_language(client, admin):
    response = client.post("/api/demos", headers={**admin, "Accept-Language": "fr"},
                           json={**DEMO, "video_url": "https://example.com/video.mp4"})
    assert response.status_code == 422
    assert "Google Drive, YouTube ou Vimeo" in response.json()["detail"]


def test_a_preview_image_comes_from_drive_only(client, admin):
    refused = create(client, admin, thumbnail_url="https://example.com/image.png")
    assert refused.status_code == 422 and refused.json()["code"] == "demo.thumbnail_drive_only"
    kept = create(client, admin, thumbnail_url="https://drive.google.com/file/d/IMG12345678/view")
    assert kept.json()["preview_image"] == "https://drive.google.com/thumbnail?id=IMG12345678&sz=w1280"


def test_only_the_fields_sent_change(client, admin):
    demo = create(client, admin, service="cloud").json()
    changed = client.patch(f"/api/demos/{demo['id']}", headers=admin, json={"published": True}).json()
    assert (changed["published"], changed["service"], changed["title_fr"]) == (True, "cloud", DEMO["title_fr"])
    cleared = client.patch(f"/api/demos/{demo['id']}", headers=admin, json={"service": None}).json()
    assert cleared["service"] is None


def test_changing_the_link_changes_the_provider(client, admin):
    demo = create(client, admin).json()
    moved = client.patch(f"/api/demos/{demo['id']}", headers=admin,
                         json={"video_url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    assert (moved["provider"], moved["video_id"]) == ("youtube", "dQw4w9WgXcQ")


def test_the_whole_order_is_set_at_once(client, admin):
    ids = [create(client, admin, title_fr=f"Démo {n}", title_en=f"Demo {n}").json()["id"] for n in range(3)]
    response = client.put("/api/demos/order", headers=admin, json={"ids": [ids[2], ids[0], ids[1]]})
    assert response.status_code == 200, response.text
    listed = client.get("/api/demos", headers=admin).json()
    assert [d["id"] for d in listed] == [ids[2], ids[0], ids[1]]


@pytest.mark.parametrize("pick", [lambda ids: ids[:2], lambda ids: ids + [ids[0]], lambda ids: ids[:2] + [999999]])
def test_an_order_that_misses_or_repeats_a_demo_is_refused(client, admin, pick):
    ids = [create(client, admin, title_fr=f"Démo {n}", title_en=f"Demo {n}").json()["id"] for n in range(3)]
    response = client.put("/api/demos/order", headers=admin, json={"ids": pick(ids)})
    assert response.status_code == 422 and response.json()["code"] == "demo.order_mismatch"


def test_a_demo_is_deleted(client, admin):
    demo = create(client, admin).json()
    assert client.delete(f"/api/demos/{demo['id']}", headers=admin).status_code == 204
    assert client.get("/api/demos", headers=admin).json() == []
    assert client.delete(f"/api/demos/{demo['id']}", headers=admin).status_code == 404


def test_every_change_is_audited(client, admin, database):
    demo = create(client, admin).json()
    client.patch(f"/api/demos/{demo['id']}", headers=admin, json={"published": True})
    other = create(client, admin, title_fr="Autre", title_en="Other").json()
    client.put("/api/demos/order", headers=admin, json={"ids": [other["id"], demo["id"]]})
    client.delete(f"/api/demos/{demo['id']}", headers=admin)
    with database.connect() as c:
        actions = c.execute(text("SELECT action FROM audit_events WHERE entity = 'demo' ORDER BY id")).scalars().all()
        deleted = c.execute(text("SELECT before FROM audit_events WHERE action = 'demo.deleted'")).scalar_one()
    assert actions == ["demo.created", "demo.updated", "demo.created", "demo.reordered", "demo.deleted"]
    assert deleted["video_url"] == DRIVE


# --- The website reads the published ones -------------------------------------------

def test_the_website_sees_published_demos_only_in_order(client, admin):
    hidden = create(client, admin, title_fr="Cachée", title_en="Hidden").json()
    shown = create(client, admin, published=True).json()
    second = create(client, admin, title_fr="Deuxième", title_en="Second", published=True,
                    video_url="https://vimeo.com/76979871").json()
    client.put("/api/demos/order", headers=admin, json={"ids": [second["id"], hidden["id"], shown["id"]]})

    response = client.get("/api/public/demos")
    assert response.status_code == 200
    body = response.json()
    assert [d["id"] for d in body] == [second["id"], shown["id"]]
    # Both languages, the player and the preview; nothing internal.
    assert set(body[1]) == {"id", "title_fr", "title_en", "description_fr", "description_en", "provider",
                            "service", "embed_url", "preview_image"}
    assert body[0]["preview_image"] is None  # Vimeo without an image: the website's fallback
    assert response.headers["cache-control"] == "public, max-age=60"


def test_no_published_demo_is_an_empty_list(client, admin):
    create(client, admin)
    assert client.get("/api/public/demos").json() == []


def test_an_anonymous_caller_cannot_read_the_table_even_in_sql(client, admin):
    """The website reads through the function only; the table stays closed."""
    import os

    from sqlalchemy import create_engine

    create(client, admin, published=True)
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as c:
            assert c.execute(text("SELECT count(*) FROM demo_videos")).scalar() == 0
            assert c.execute(text("SELECT count(*) FROM published_demos()")).scalar() == 1
    finally:
        engine.dispose()


def test_the_accountant_does_not_see_the_table(client, identities, admin):
    create(client, admin, published=True)
    assert client.get("/api/demos", headers=identities["accountant"]["headers"]).status_code == 403
