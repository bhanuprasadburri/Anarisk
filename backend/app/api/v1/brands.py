import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import Pagination, require_permission
from app.core.config import get_settings
from app.core.errors import ValidationFailure
from app.db.session import get_db
from app.models import User
from app.models.enums import Provenance
from app.repositories.access import get_brand_for_user
from app.schemas.brand import BrandCreate, BrandDetail, BrandOut, BrandUpdate, ReferenceCreate, ReferenceOut
from app.schemas.common import Message, Page
from app.services import brands as svc

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.post("", response_model=BrandOut, status_code=201)
def create_brand(body: BrandCreate, user: User = Depends(require_permission("brand:write")), db: Session = Depends(get_db)):
    return svc.create_brand(db, user, body)


@router.get("", response_model=Page[BrandOut])
def list_brands(p: Pagination = Depends(), q: str | None = Query(None, max_length=100), user: User = Depends(require_permission("brand:read")), db: Session = Depends(get_db)):
    rows, total = svc.list_brands(db, user, p.page, p.page_size, q)
    return Page.build([BrandOut.model_validate(r) for r in rows], total, p.page, p.page_size)


@router.get("/{brand_id}", response_model=BrandDetail, summary="Brand with its official references")
def get_brand(brand_id: uuid.UUID, user: User = Depends(require_permission("brand:read")), db: Session = Depends(get_db)):
    b = get_brand_for_user(db, user, brand_id)
    out = BrandDetail.model_validate(b)
    out.entity_count = svc.brand_entity_count(db, b.id)
    return out


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: uuid.UUID, body: BrandUpdate, user: User = Depends(require_permission("brand:write")), db: Session = Depends(get_db)):
    return svc.update_brand(db, user, brand_id, body)


@router.post("/{brand_id}/references", response_model=ReferenceOut, status_code=201, summary="Register an official name/handle/domain/app/publisher/bio, or an image by perceptual hash")
def add_reference(brand_id: uuid.UUID, body: ReferenceCreate, user: User = Depends(require_permission("brand:write")), db: Session = Depends(get_db)):
    return svc.add_reference(db, user, brand_id, body)


@router.post("/{brand_id}/references/image", response_model=ReferenceOut, status_code=201, summary="Upload an official logo/image (validated by content; hashed with pHash)")
async def add_image_reference(brand_id: uuid.UUID, file: UploadFile = File(...), note: str | None = Form(None, max_length=500),
                              user: User = Depends(require_permission("brand:write")), db: Session = Depends(get_db)):
    data = await file.read(get_settings().max_upload_bytes + 1)
    return svc.add_image_reference(db, user, brand_id, data, note, Provenance.MANUAL)


@router.delete("/{brand_id}/references/{reference_id}", response_model=Message)
def delete_reference(brand_id: uuid.UUID, reference_id: uuid.UUID, user: User = Depends(require_permission("brand:write")), db: Session = Depends(get_db)):
    svc.delete_reference(db, user, brand_id, reference_id)
    return Message(message="Reference deleted")
