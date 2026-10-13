import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import Pagination, require_permission
from app.core.config import get_settings
from app.core.errors import ValidationFailure
from app.db.session import get_db
from app.models import User
from app.models.enums import EvidenceKind, Provenance
from app.schemas.common import Page
from app.schemas.evidence import EvidenceCreate, EvidenceOut
from app.services import evidence as svc
from app.services.cases import _ev

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("", response_model=EvidenceOut, status_code=201, summary="Attach text/URL/WHOIS/other evidence metadata to an entity")
def create(body: EvidenceCreate, user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    return _ev(svc.create_evidence(db, user, body))


@router.post("/upload", response_model=EvidenceOut, status_code=201, summary="Upload an image/screenshot (PNG/JPEG/WEBP/GIF, content-validated, size-limited)")
async def upload(entity_id: uuid.UUID = Form(...), title: str = Form(..., min_length=1, max_length=300), description: str | None = Form(None, max_length=5000),
                 kind: EvidenceKind = Form(EvidenceKind.SCREENSHOT), provenance: Provenance = Form(Provenance.MANUAL), file: UploadFile = File(...),
                 user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    if kind not in (EvidenceKind.SCREENSHOT, EvidenceKind.IMAGE):
        raise ValidationFailure("Uploads must have kind 'screenshot' or 'image'")
    if provenance == Provenance.COLLECTED:
        raise ValidationFailure("provenance 'collected' is reserved for connectors")
    data = await file.read(get_settings().max_upload_bytes + 1)
    return _ev(svc.upload_image_evidence(db, user, entity_id, data, title=title, description=description, kind=kind, provenance=provenance, original_filename=file.filename))


@router.get("", response_model=Page[EvidenceOut])
def list_(p: Pagination = Depends(), entity_id: uuid.UUID | None = None, kind: EvidenceKind | None = None,
          user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    rows, total = svc.list_evidence(db, user, p.page, p.page_size, entity_id, kind)
    return Page.build([_ev(r) for r in rows], total, p.page, p.page_size)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get(evidence_id: uuid.UUID, user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    return _ev(svc.get_evidence(db, user, evidence_id))


@router.get("/{evidence_id}/file", summary="Download the stored image (served as an attachment with nosniff)")
def file(evidence_id: uuid.UUID, user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    ev = svc.get_evidence(db, user, evidence_id)
    return FileResponse(svc.evidence_file_path(ev), media_type=ev.content_type or "application/octet-stream", filename=f"{ev.sha256[:16]}",
                        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'"})
