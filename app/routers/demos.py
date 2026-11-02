"""Demo videos (#232, part of #230): managed by the admin, shown on the website.

The admin routes act on demo_videos under row-level security that only lets
the admin in. GET /api/public/demos is public: it is listed in
main.PUBLIC_PATHS, and it reads only through published_demos(), a SECURITY
DEFINER function returning the public fields of published demos - never the
table, so a hidden demo or an internal column cannot leak.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.i18n import ApiError
from app.models.demo import DemoVideo
from app.models.user import User
from app.schemas.demo import DemoIn, DemoOrder, DemoOut, DemoUpdate, PublicDemoOut
from app.services import demo_links, throttle
from app.services.audit import record_event

public = APIRouter()
admin = APIRouter()
ADMIN = require_roles("admin")

# Fields worth keeping in the audit trail when they change.
AUDITED = ("title_fr", "title_en", "description_fr", "description_en", "video_url", "thumbnail_url",
           "service", "published")


def _out(demo: DemoVideo) -> DemoOut:
    return DemoOut(
        id=demo.id, title_fr=demo.title_fr, title_en=demo.title_en,
        description_fr=demo.description_fr, description_en=demo.description_en,
        video_url=demo.video_url, provider=demo.provider, video_id=demo.video_id,
        thumbnail_url=demo.thumbnail_url, service=demo.service, position=demo.position,
        published=demo.published, created_at=demo.created_at, updated_at=demo.updated_at,
        embed_url=demo_links.embed_url(demo.provider, demo.video_id),
        preview_image=demo_links.preview_image(demo.provider, demo.video_id, demo.thumbnail_url),
    )


def _video(url: str) -> demo_links.VideoLink:
    found = demo_links.parse_video_link(url)
    if found is None:
        raise ApiError(422, "demo.link_unknown")
    return found


def _thumbnail(url: str | None) -> str | None:
    """The admin's image link, checked; "" means none."""
    if not url:
        return None
    if demo_links.parse_drive_image(url) is None:
        raise ApiError(422, "demo.thumbnail_drive_only")
    return url


def _get(db: Session, demo_id: int) -> DemoVideo:
    demo = db.get(DemoVideo, demo_id)
    if demo is None:
        raise ApiError(404, "demo.not_found")
    return demo


# --- Public ------------------------------------------------------------------------

@public.get("/public/demos", response_model=list[PublicDemoOut], dependencies=[Depends(throttle.limit_public_requests)])
def published_demos(response: Response, db: Session = Depends(get_db)):
    """The published demos, in display order, for the website's Demo section."""
    rows = db.execute(text("SELECT * FROM published_demos()")).mappings().all()
    # The section changes rarely; a short cache spares the database on a busy page.
    response.headers["Cache-Control"] = "public, max-age=60"
    return [
        PublicDemoOut(
            id=r["id"], title_fr=r["title_fr"], title_en=r["title_en"],
            description_fr=r["description_fr"], description_en=r["description_en"],
            provider=r["provider"], service=r["service"],
            embed_url=demo_links.embed_url(r["provider"], r["video_id"]),
            preview_image=demo_links.preview_image(r["provider"], r["video_id"], r["thumbnail_url"]),
        )
        for r in rows
    ]


# --- Admin -------------------------------------------------------------------------

@admin.get("/demos", response_model=list[DemoOut])
def list_demos(db: Session = Depends(get_db), _: User = Depends(ADMIN)):
    """Every demo, published or hidden, in display order."""
    return [_out(d) for d in db.query(DemoVideo).order_by(DemoVideo.position, DemoVideo.id).all()]


@admin.post("/demos", response_model=DemoOut, status_code=201)
def create_demo(payload: DemoIn, db: Session = Depends(get_db), user: User = Depends(ADMIN)):
    """Add a demo, last in the order. Hidden unless `published` is sent."""
    video = _video(payload.video_url)
    last = db.query(func.max(DemoVideo.position)).scalar()
    demo = DemoVideo(
        **payload.model_dump(exclude={"thumbnail_url"}),
        thumbnail_url=_thumbnail(payload.thumbnail_url),
        provider=video.provider, video_id=video.video_id,
        position=0 if last is None else last + 1,
        created_by_id=user.id, updated_by_id=user.id,
    )
    db.add(demo)
    db.flush()
    record_event(db, "demo.created", "demo", demo.id,
                 after={**{k: getattr(demo, k) for k in AUDITED}, "position": demo.position})
    db.commit()
    db.refresh(demo)
    return _out(demo)


@admin.patch("/demos/{demo_id}", response_model=DemoOut)
def update_demo(demo_id: int, payload: DemoUpdate, db: Session = Depends(get_db), user: User = Depends(ADMIN)):
    """Correct a demo, publish or hide it: only the fields sent change."""
    demo = _get(db, demo_id)
    # Sent as null: ignored, except for the two optional fields, where it clears them.
    changes = {k: v for k, v in payload.model_dump(exclude_unset=True).items()
               if v is not None or k in ("thumbnail_url", "service")}
    if "video_url" in changes:
        video = _video(changes["video_url"])
        changes["provider"], changes["video_id"] = video.provider, video.video_id
    if "thumbnail_url" in changes:
        changes["thumbnail_url"] = _thumbnail(changes["thumbnail_url"])
    before = {k: getattr(demo, k) for k in changes if getattr(demo, k) != changes[k]}
    after = {k: changes[k] for k in before}
    if after:
        for field, value in after.items():
            setattr(demo, field, value)
        demo.updated_by_id = user.id
        demo.updated_at = datetime.now(timezone.utc)
        record_event(db, "demo.updated", "demo", demo.id,
                     before={k: v for k, v in before.items() if k in AUDITED},
                     after={k: v for k, v in after.items() if k in AUDITED})
        db.commit()
        db.refresh(demo)
    return _out(demo)


@admin.put("/demos/order", response_model=list[DemoOut])
def reorder_demos(payload: DemoOrder, db: Session = Depends(get_db), user: User = Depends(ADMIN)):
    """Set the whole order at once: every demo, each exactly once.

    One request for the whole list, so two admins reordering at the same time
    cannot leave two demos on the same position.
    """
    demos = {d.id: d for d in db.query(DemoVideo).with_for_update().all()}
    if len(payload.ids) != len(set(payload.ids)) or set(payload.ids) != set(demos):
        raise ApiError(422, "demo.order_mismatch")
    before = [d.id for d in sorted(demos.values(), key=lambda d: (d.position, d.id))]
    for position, demo_id in enumerate(payload.ids):
        demos[demo_id].position = position
        demos[demo_id].updated_by_id = user.id
    if before != payload.ids:
        record_event(db, "demo.reordered", "demo", "order", before={"order": before}, after={"order": payload.ids})
    db.commit()
    return [_out(demos[i]) for i in payload.ids]


@admin.delete("/demos/{demo_id}", status_code=204)
def delete_demo(demo_id: int, db: Session = Depends(get_db), _: User = Depends(ADMIN)):
    """Delete a demo. The video itself stays where it is hosted; the audit trail keeps what it was."""
    demo = _get(db, demo_id)
    record_event(db, "demo.deleted", "demo", demo.id,
                 before={"title_fr": demo.title_fr, "title_en": demo.title_en, "video_url": demo.video_url,
                         "published": demo.published})
    db.delete(demo)
    db.commit()
    return Response(status_code=204)
