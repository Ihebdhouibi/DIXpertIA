"""Demo videos (#232): link recognition, the admin's routes, and the website's read.

No video file is stored: a demo is a link to Drive, YouTube or Vimeo. The
admin manages demos; the website reads the published ones through
published_demos(), never the table. Preview images are fetched by the server
when a demo is saved and served from our domain; here the fetch is replaced
by a stand-in, so no test touches the network.
"""

import io

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


def jpeg(width=64, height=36) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (width, height), (16, 19, 20)).save(out, format="JPEG")
    return out.getvalue()


# The real preview fetch, kept before the fixture below replaces it.
REAL = {}


@pytest.fixture(autouse=True)
def fetched(monkeypatch):
    """The preview fetch, without the network: an image for Drive and YouTube, none for Vimeo.

    Each call is recorded, so a test can see what was asked for.
    """
    from app.services import demo_previews

    calls = []
    REAL.setdefault("fetch", demo_previews.fetch)

    def fake(provider, video_id, thumbnail_url):
        calls.append((provider, video_id, thumbnail_url))
        if provider == "vimeo" and not thumbnail_url:
            return None
        return jpeg(), f"https://example.test/{provider}/{video_id}.jpg"

    monkeypatch.setattr(demo_previews, "fetch", fake)
    return calls


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


def test_the_players_built_from_a_link():
    from app.services.demo_links import embed_url

    assert embed_url("drive", "1AbCdEfGhIjKlMnOp") == "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/preview"
    assert embed_url("youtube", "dQw4w9WgXcQ").startswith("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
    assert embed_url("vimeo", "76979871-8272103f6e") == "https://player.vimeo.com/video/76979871?dnt=1&h=8272103f6e"


# --- Where previews come from, and what is kept of them ------------------------------

def test_where_each_preview_is_fetched_from():
    from app.services.demo_previews import source_url

    # The admin's Drive image wins; otherwise the platform's own thumbnail.
    assert source_url("drive", "VID12345678", "https://drive.google.com/file/d/IMG12345678/view") \
        == "https://drive.google.com/thumbnail?id=IMG12345678&sz=w1280"
    assert source_url("drive", "VID12345678", None) == "https://drive.google.com/thumbnail?id=VID12345678&sz=w1280"
    assert source_url("youtube", "dQw4w9WgXcQ", None) == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    # Vimeo publishes its thumbnail through oEmbed, unlisted hash included.
    assert source_url("vimeo", "76979871-8272103f6e", None).startswith(
        "https://vimeo.com/api/oembed.json?url=https%3A%2F%2Fvimeo.com%2F76979871%2F8272103f6e")


@pytest.mark.parametrize("url,allowed", [
    ("https://drive.google.com/thumbnail?id=x", True),
    ("https://lh3.googleusercontent.com/abc", True),
    ("https://i.ytimg.com/vi/x/hqdefault.jpg", True),
    ("https://i.vimeocdn.com/video/1.jpg", True),
    ("http://i.ytimg.com/vi/x/hqdefault.jpg", False),          # not https
    ("https://169.254.169.254/latest/meta-data", False),         # the cloud metadata address
    ("https://localhost:8000/api/demos", False),
    ("https://googleusercontent.com.evil.example/x", False),
    ("https://example.com/image.png", False),
])
def test_the_server_fetches_from_the_video_hosts_only(url, allowed):
    from app.services.demo_previews import _allowed

    assert _allowed(url) is allowed


def test_a_redirect_to_another_host_is_refused():
    import urllib.error
    import urllib.request

    from app.services.demo_previews import _OnlyAllowedRedirects

    request = urllib.request.Request("https://drive.google.com/thumbnail?id=x")
    with pytest.raises(urllib.error.URLError):
        _OnlyAllowedRedirects().redirect_request(request, None, 302, "Found", {}, "https://example.com/x.png")


def test_a_preview_is_kept_as_a_small_jpeg_and_anything_else_is_refused():
    from PIL import Image

    from app.services.demo_previews import to_jpeg

    big = io.BytesIO()
    Image.new("RGBA", (3000, 2000), (198, 242, 78, 255)).save(big, format="PNG")
    kept = Image.open(io.BytesIO(to_jpeg(big.getvalue())))
    assert kept.format == "JPEG" and kept.size[0] <= 1280 and kept.size[1] <= 720
    with pytest.raises(Exception):
        to_jpeg(b"<html>Sign in to Google Drive</html>")  # a Drive file that is not shared


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
    assert kept.status_code == 201


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
    # Drive's preview is served from our own domain, never from Google.
    assert body[1]["preview_image"].startswith(f"/api/public/demos/{shown['id']}/preview?v=")
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


# --- Previews, served from our domain --------------------------------------------------

def test_a_published_demos_preview_is_served_publicly(client, admin):
    demo = create(client, admin, published=True).json()
    url = client.get("/api/public/demos").json()[0]["preview_image"]
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert "immutable" in response.headers["cache-control"]
    assert response.content.startswith(b"\xff\xd8")  # a JPEG
    assert demo["preview_image"].startswith(f"/api/demos/{demo['id']}/preview?v=")


def test_a_hidden_demos_preview_is_not_public_but_the_admin_sees_it(client, admin):
    demo = create(client, admin).json()
    assert client.get(f"/api/public/demos/{demo['id']}/preview").status_code == 404
    assert client.get(f"/api/demos/{demo['id']}/preview").status_code == 401
    seen = client.get(f"/api/demos/{demo['id']}/preview", headers=admin)
    assert seen.status_code == 200 and seen.headers["content-type"] == "image/jpeg"


def test_the_admins_image_is_what_gets_fetched(client, admin, fetched):
    image = "https://drive.google.com/file/d/IMG12345678/view"
    create(client, admin, thumbnail_url=image)
    assert fetched[-1] == ("drive", "1AbCdEfGhIjKlMnOpQrStUvWxYz012345", image)


def test_a_failed_fetch_saves_the_demo_without_a_preview(client, admin):
    demo = create(client, admin, video_url="https://vimeo.com/76979871")
    assert demo.status_code == 201 and demo.json()["preview_image"] is None


def test_a_new_link_replaces_the_preview_or_drops_it(client, admin, fetched, database):
    demo = create(client, admin).json()
    # A title change does not fetch again.
    calls = len(fetched)
    client.patch(f"/api/demos/{demo['id']}", headers=admin, json={"title_en": "Renamed"})
    assert len(fetched) == calls
    # A new link whose preview cannot be fetched: the old image goes, it would show the wrong video.
    moved = client.patch(f"/api/demos/{demo['id']}", headers=admin, json={"video_url": "https://vimeo.com/76979871"})
    assert moved.json()["preview_image"] is None
    with database.connect() as c:
        assert c.execute(text("SELECT count(*) FROM demo_previews")).scalar() == 0


def test_saving_a_demo_without_a_preview_tries_again(client, admin, fetched):
    demo = create(client, admin, video_url="https://vimeo.com/76979871").json()
    calls = len(fetched)
    client.patch(f"/api/demos/{demo['id']}", headers=admin, json={"title_en": "Retry"})
    assert len(fetched) == calls + 1


def test_a_preview_goes_with_its_demo(client, admin, database):
    demo = create(client, admin).json()
    client.delete(f"/api/demos/{demo['id']}", headers=admin)
    with database.connect() as c:
        assert c.execute(text("SELECT count(*) FROM demo_previews")).scalar() == 0


# --- The fetch itself, with the network replaced -------------------------------------

class _Response:
    def __init__(self, body: bytes, content_type: str):
        self.body, self.headers = body, {"Content-Type": content_type}

    def read(self, limit):
        return self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def network(monkeypatch):
    """The opener the fetch uses, answering with whatever the test sets."""
    from app.services import demo_previews

    answer = {}

    def open_(request, timeout):
        if "error" in answer:
            raise answer["error"]
        return _Response(answer["body"], answer["type"])

    monkeypatch.setattr(demo_previews._opener, "open", open_)
    return answer


def real_fetch():
    """The real fetch, kept aside by the autouse fixture before it replaces it."""
    return REAL["fetch"]


@pytest.mark.parametrize("content_type", ["image/jpeg", "image/png", "image/webp"])
def test_a_fetched_image_is_kept(network, content_type):
    from PIL import Image

    raw = io.BytesIO()
    Image.new("RGB", (32, 18), (1, 2, 3)).save(raw, format=content_type.split("/")[1].upper())
    network.update(body=raw.getvalue(), type=content_type)
    content, source = real_fetch()("youtube", "dQw4w9WgXcQ", None)
    assert content.startswith(b"\xff\xd8") and source == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"


@pytest.mark.parametrize("body,content_type", [
    (b"<html>Sign in</html>", "text/html"),          # a Drive file that is not shared
    (b"GIF89a", "image/gif"),                         # not an accepted type
    (b"<svg/>", "image/jpeg"),                        # announced as an image, but is not one
    (b"\xff\xd8" + b"0" * 2_000_001, "image/jpeg"),     # too large
], ids=["html", "gif", "fake-jpeg", "too-large"])
def test_anything_but_a_small_image_gives_no_preview(network, body, content_type):
    network.update(body=body, type=content_type)
    assert real_fetch()("drive", "1AbCdEfGhIjKlMnOp", None) is None


def test_a_network_failure_gives_no_preview(network):
    import urllib.error

    network["error"] = urllib.error.URLError("timed out")
    assert real_fetch()("drive", "1AbCdEfGhIjKlMnOp", None) is None


def test_redirects_are_capped():
    from app.services.demo_previews import MAX_REDIRECTS, _OnlyAllowedRedirects

    assert _OnlyAllowedRedirects.max_redirections == MAX_REDIRECTS == 3


def test_reordering_records_who_and_when_on_the_moved_demos_only(client, admin, database):
    first = create(client, admin, title_fr="Un", title_en="One").json()
    second = create(client, admin, title_fr="Deux", title_en="Two").json()
    third = create(client, admin, title_fr="Trois", title_en="Three").json()
    client.put("/api/demos/order", headers=admin, json={"ids": [second["id"], first["id"], third["id"]]})
    with database.connect() as c:
        changed = dict(c.execute(text("SELECT id, updated_at > created_at FROM demo_videos")).all())
    assert changed == {first["id"]: True, second["id"]: True, third["id"]: False}
