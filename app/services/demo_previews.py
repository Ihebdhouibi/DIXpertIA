"""Fetch a demo's preview image once, so the website serves it itself (#232, #231).

The website must not contact Google, YouTube or Vimeo before a visitor
presses Play, so preview images are not linked from those hosts: the server
fetches the image when the demo is saved, re-encodes it and stores it
(demo_previews, migration 9d098021263d).

The server fetches only URLs it builds itself, from a recognised provider and
id, and follows redirects only to the hosts those providers serve images
from. A response that is not an image, too large or too slow gives no
preview; the website then shows its branded fallback. Saving a demo never
fails because of its preview.
"""

import io
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

from app.services import demo_links

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 6
MAX_DOWNLOAD_BYTES = 5_000_000
MAX_SIZE = (1280, 720)
JPEG_QUALITY = 82
# Where previews may come from, redirects included: Drive's thumbnail answers
# with a redirect to googleusercontent.com.
ALLOWED_HOSTS = ("drive.google.com", ".googleusercontent.com", "i.ytimg.com", "vimeo.com", "i.vimeocdn.com")


def _allowed(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    return parts.scheme == "https" and any(
        host == allowed or (allowed.startswith(".") and host.endswith(allowed)) for allowed in ALLOWED_HOSTS)


class _OnlyAllowedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _allowed(newurl):
            host = urllib.parse.urlsplit(newurl).hostname
            raise urllib.error.URLError(f"redirect to a host that is not allowed: {host}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_OnlyAllowedRedirects)


def _get(url: str) -> bytes:
    """GET an allowed URL, at most MAX_DOWNLOAD_BYTES."""
    if not _allowed(url):
        raise ValueError(f"host not allowed: {urllib.parse.urlsplit(url).hostname}")
    request = urllib.request.Request(url, headers={"User-Agent": "DI Xpertia preview fetcher"})
    with _opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(body) > MAX_DOWNLOAD_BYTES:
        raise ValueError("preview larger than the limit")
    return body


def source_url(provider: str, video_id: str, thumbnail_url: str | None) -> str | None:
    """Where this demo's preview comes from: the admin's Drive image, else the platform's thumbnail."""
    if thumbnail_url:
        image_id = demo_links.parse_drive_image(thumbnail_url)
        return demo_links.drive_thumbnail(image_id) if image_id else None
    if provider == "drive":
        return demo_links.drive_thumbnail(video_id)
    if provider == "youtube":
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    if provider == "vimeo":
        number, _, unlisted = video_id.partition("-")
        page = f"https://vimeo.com/{number}" + (f"/{unlisted}" if unlisted else "")
        return "https://vimeo.com/api/oembed.json?" + urllib.parse.urlencode({"url": page, "width": 1280})
    return None


def to_jpeg(raw: bytes) -> bytes:
    """Any image as a JPEG of at most 1280 x 720: metadata dropped, nothing but pixels kept."""
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        picture = image.convert("RGB")
    picture.thumbnail(MAX_SIZE)
    out = io.BytesIO()
    picture.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()


def fetch(provider: str, video_id: str, thumbnail_url: str | None) -> tuple[bytes, str] | None:
    """(JPEG bytes, source URL) for this demo's preview, or None when there is none to be had."""
    url = source_url(provider, video_id, thumbnail_url)
    if url is None:
        return None
    try:
        if url.startswith("https://vimeo.com/api/oembed.json"):
            url = json.loads(_get(url)).get("thumbnail_url") or ""
            if not url:
                return None
        return to_jpeg(_get(url)), url
    except Exception as exc:  # network, refused redirect, not an image: no preview, the save goes on
        log.warning("Demo preview not fetched from %s: %s", urllib.parse.urlsplit(url).hostname, exc)
        return None
