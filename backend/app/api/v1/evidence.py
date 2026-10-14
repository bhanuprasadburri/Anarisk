import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, require_permission
from app.core.config import get_settings
from app.core.errors import ValidationFailure
from app.db.session import get_db
from app.models import User
from app.models.enums import EvidenceKind, Provenance
from app.schemas.common import Page
from app.schemas.evidence import EvidenceCreate, EvidenceLinkRequest, EvidenceOut, EvidenceVerification
from app.services import evidence as svc

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("", response_model=EvidenceOut, status_code=201, summary="Attach text/URL/WHOIS/other evidence metadata to an entity")
def create(body: EvidenceCreate, user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    return svc.to_out(db, svc.create_evidence(db, user, body))


@router.post("/upload", response_model=EvidenceOut, status_code=201, summary="Upload an image/screenshot (PNG/JPEG/WEBP/GIF, content-validated, size-limited)")
async def upload(entity_id: uuid.UUID = Form(...), title: str = Form(..., min_length=1, max_length=300), description: str | None = Form(None, max_length=5000),
                 kind: EvidenceKind = Form(EvidenceKind.SCREENSHOT), provenance: Provenance = Form(Provenance.MANUAL), file: UploadFile = File(...),
                 user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    if kind not in (EvidenceKind.SCREENSHOT, EvidenceKind.IMAGE):
        raise ValidationFailure("Uploads must have kind 'screenshot' or 'image'")
    if provenance == Provenance.COLLECTED:
        raise ValidationFailure("provenance 'collected' is reserved for connectors")
    data = await file.read(get_settings().max_upload_bytes + 1)
    return svc.to_out(db, svc.upload_image_evidence(db, user, entity_id, data, title=title, description=description, kind=kind, provenance=provenance, original_filename=file.filename))


@router.get("/export/csv", summary="CSV export of every evidence record in your scope (attachment download)")
@router.get("/export", summary="CSV export of every evidence record in your scope (alias used by the web app)")
def export_csv(entity_id: uuid.UUID | None = None, kind: EvidenceKind | None = None, case_id: uuid.UUID | None = None,
               verification_status: str | None = Query(None, pattern="^(verified|mismatch|pending)$"),
               q: str | None = Query(None, max_length=100),
               user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    filename, content = svc.export_csv(db, user, entity_id, kind, case_id, verification_status, q)
    return Response(content=content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("", response_model=Page[EvidenceOut],
            summary="List evidence: filters entity_id, kind, case_id (entity-linked or directly attached), verification_status, q; sort created_at|collected_at|title|size_bytes")
def list_(p: Pagination = Depends(), entity_id: uuid.UUID | None = None, kind: EvidenceKind | None = None,
          case_id: uuid.UUID | None = None,
          verification_status: str | None = Query(None, pattern="^(verified|mismatch|pending)$"),
          q: str | None = Query(None, max_length=100),
          sort: str = Query("created_at", pattern="^(created_at|collected_at|title|size_bytes)$"),
          order: str = Query("desc", pattern="^(asc|desc)$"),
          user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    rows, total = svc.list_evidence(db, user, p.page, p.page_size, entity_id, kind, case_id, verification_status, q, sort, order)
    return Page.build(svc.hydrate(db, rows), total, p.page, p.page_size)


@router.get("/{evidence_id}", response_model=EvidenceOut, summary="Evidence detail incl. case links and verification status")
def get(evidence_id: uuid.UUID, user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    return svc.to_out(db, svc.get_evidence(db, user, evidence_id))


@router.get("/{evidence_id}/file", summary="Download the stored image (served as an attachment with nosniff)")
def file(evidence_id: uuid.UUID, user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    ev = svc.get_evidence(db, user, evidence_id)
    return FileResponse(svc.evidence_file_path(ev), media_type=ev.content_type or "application/octet-stream", filename=f"{ev.sha256[:16]}",
                        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'"})


@router.get("/{evidence_id}/download", summary="Authenticated download (same bytes as /file; used by the web app's save dialog)")
def download(evidence_id: uuid.UUID, user: User = Depends(require_permission("evidence:read")), db: Session = Depends(get_db)):
    return file(evidence_id, user=user, db=db)


@router.post("/{evidence_id}/verify", response_model=EvidenceVerification,
             summary="Recompute the sha256 of the stored bytes and record verified/mismatch (honest, no fabrication)")
def verify(evidence_id: uuid.UUID, user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    return svc.verify_evidence(db, user, evidence_id)


@router.post("/{evidence_id}/link", response_model=EvidenceOut,
             summary="Link this evidence to a case and/or (re)attach it to an entity")
def link(evidence_id: uuid.UUID, body: EvidenceLinkRequest, user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    if body.case_id is None and body.entity_id is None:
        raise ValidationFailure("Provide case_id and/or entity_id")
    ev = svc.link_evidence(db, user, evidence_id, case_id=body.case_id, entity_id=body.entity_id)
    out = svc.to_out(db, ev)
    out.case_ids = svc.case_ids_for(db, ev.id)
    return out


@router.delete("/{evidence_id}/link/{case_id}", status_code=204, summary="Remove the case link (the evidence itself is kept)")
def unlink(evidence_id: uuid.UUID, case_id: uuid.UUID, user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    svc.unlink_from_case(db, user, evidence_id, case_id)


@router.delete("/{evidence_id}/link", status_code=204,
               summary="Remove the case and/or entity link given as query parameters (web app variant)")
def unlink_query(evidence_id: uuid.UUID, case_id: uuid.UUID | None = None, entity_id: uuid.UUID | None = None,
                 user: User = Depends(require_permission("evidence:write")), db: Session = Depends(get_db)):
    if case_id is None and entity_id is None:
        raise ValidationFailure("Provide case_id and/or entity_id")
    svc.unlink_evidence(db, user, evidence_id, case_id=case_id, entity_id=entity_id)


@router.delete("/{evidence_id}", status_code=204, summary="Delete evidence (administrators and investigators; removes the stored file too)")
def delete(evidence_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc.delete_evidence(db, user, evidence_id)
