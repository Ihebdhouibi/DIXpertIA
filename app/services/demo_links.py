"""Recognise a demo's video link, and build what the website needs to show it (#232).

The admin pastes a share link; nothing is stored but the link and what is
recognised in it. From the provider and the video id the API builds:
- the player to embed, loaded only when a visitor clicks Play;
- a preview image when the admin gave none.

Only three providers are recognised, in their usual share formats. Anything
else is refused, so the website never frames an arbitrary page, and the
site's Content-Security-Policy can name exactly these players
(deploy/app/security-headers.conf).
"""

import re
from typing import NamedTuple
from urllib.parse import parse_qs, urlsplit


class VideoLink(NamedTuple):
    provider: str
    video_id: str


_DRIVE_ID = r"[A-Za-z0-9_-]{10,100}"
_YOUTUBE_ID = r"[A-Za-z0-9_-]{11}"
_DRIVE_HOSTS = {"drive.google.com", "docs.google.com"}
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com",
                  "www.youtube-nocookie.com"}
_VIMEO_HOSTS = {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}


def _drive_id(parts) -> str | None:
    match = re.fullmatch(rf"/file/d/({_DRIVE_ID})(?:/[^/]*)?/?", parts.path)
    if match:
        return match.group(1)
    if parts.path in ("/open", "/uc", "/thumbnail"):
        found = parse_qs(parts.query).get("id", [""])[0]
        if re.fullmatch(_DRIVE_ID, found):
            return found
    return None


def parse_video_link(url: str) -> VideoLink | None:
    """The provider and video id of a Drive, YouTube or Vimeo link, or None."""
    parts = urlsplit((url or "").strip())
    if parts.scheme != "https":
        return None
    host = (parts.hostname or "").lower()
    if host in _DRIVE_HOSTS:
        found = _drive_id(parts)
        return VideoLink("drive", found) if found else None
    if host == "youtu.be":
        match = re.fullmatch(rf"/({_YOUTUBE_ID})/?", parts.path)
        return VideoLink("youtube", match.group(1)) if match else None
    if host in _YOUTUBE_HOSTS:
        if parts.path == "/watch":
            found = parse_qs(parts.query).get("v", [""])[0]
            return VideoLink("youtube", found) if re.fullmatch(_YOUTUBE_ID, found) else None
        match = re.fullmatch(rf"/(?:embed|shorts|live)/({_YOUTUBE_ID})/?", parts.path)
        return VideoLink("youtube", match.group(1)) if match else None
    if host in _VIMEO_HOSTS:
        # An unlisted video carries a hash: vimeo.com/123/abc or ?h=abc. It is
        # kept with the number as "123-abc", since the player needs both.
        match = re.fullmatch(r"/(?:video/)?(\d{1,12})(?:/([0-9a-f]{6,20}))?/?", parts.path)
        if not match:
            return None
        unlisted = match.group(2) or parse_qs(parts.query).get("h", [""])[0]
        if unlisted and not re.fullmatch(r"[0-9a-f]{6,20}", unlisted):
            return None
        return VideoLink("vimeo", f"{match.group(1)}-{unlisted}" if unlisted else match.group(1))
    return None


def parse_drive_image(url: str) -> str | None:
    """The file id of a Drive image link, or None. Preview images come from Drive only, for now."""
    parts = urlsplit((url or "").strip())
    if parts.scheme != "https" or (parts.hostname or "").lower() not in _DRIVE_HOSTS:
        return None
    return _drive_id(parts)


def drive_thumbnail(file_id: str) -> str:
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1280"


def embed_url(provider: str, video_id: str) -> str:
    """The player to frame. YouTube's no-cookie host, and Vimeo's do-not-track flag."""
    if provider == "drive":
        return f"https://drive.google.com/file/d/{video_id}/preview"
    if provider == "youtube":
        return f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0"
    number, _, unlisted = video_id.partition("-")
    return f"https://player.vimeo.com/video/{number}?dnt=1" + (f"&h={unlisted}" if unlisted else "")


def preview_image(provider: str, video_id: str, thumbnail_url: str | None) -> str | None:
    """The admin's image, else the platform's own thumbnail; Vimeo has none we can build."""
    if thumbnail_url:
        found = parse_drive_image(thumbnail_url)
        return drive_thumbnail(found) if found else None
    if provider == "drive":
        return drive_thumbnail(video_id)
    if provider == "youtube":
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return None
