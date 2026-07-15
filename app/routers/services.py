from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceOut

router = APIRouter()


@router.get("/", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    """Public : liste des services actifs pour le site vitrine."""
    return db.query(Service).filter(Service.actif == True).order_by(Service.ordre_affichage).all()  # noqa: E712


@router.post("/", response_model=ServiceOut, dependencies=[Depends(require_roles("admin"))])
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)):
    service = Service(**payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.put("/{service_id}", response_model=ServiceOut, dependencies=[Depends(require_roles("admin"))])
def update_service(service_id: int, payload: ServiceCreate, db: Session = Depends(get_db)):
    service = db.query(Service).get(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service introuvable")
    for key, value in payload.model_dump().items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", dependencies=[Depends(require_roles("admin"))])
def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).get(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service introuvable")
    db.delete(service)
    db.commit()
    return {"ok": True}
