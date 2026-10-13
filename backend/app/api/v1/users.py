import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import ROLE_PERMISSIONS
from app.db.session import get_db
from app.models import Organization, User
from app.models.enums import UserRole
from app.schemas.auth import OrganizationCreate, OrganizationOut, RoleInfo, UserCreate, UserOut, UserUpdate
from app.schemas.common import Page
from app.services import users as users_svc

router = APIRouter(tags=["Users & Organizations"])


@router.get("/users/roles", response_model=list[RoleInfo], summary="Roles and their permissions")
def roles(_: User = Depends(get_current_user)):
    return [RoleInfo(role=r, permissions=sorted(p)) for r, p in ROLE_PERMISSIONS.items()]


@router.get("/users/assignable", response_model=list[UserOut], summary="Active investigators/admins who can own cases in the caller's scope")
def assignable(user: User = Depends(require_permission("case:assign")), db: Session = Depends(get_db)):
    stmt = select(User).where(User.is_active.is_(True), User.role.in_([UserRole.INVESTIGATOR, UserRole.ADMIN]))
    if user.role != UserRole.ADMIN:
        stmt = stmt.where(or_(User.organization_id == user.organization_id, User.role == UserRole.ADMIN))
    return db.scalars(stmt.order_by(User.full_name)).all()


@router.get("/users", response_model=Page[UserOut], summary="List users (administrator)")
def list_users(p: Pagination = Depends(), role: UserRole | None = None, organization_id: uuid.UUID | None = None,
               is_active: bool | None = None, q: str | None = Query(None, max_length=100),
               _: User = Depends(require_permission("user:manage")), db: Session = Depends(get_db)):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if organization_id:
        stmt = stmt.where(User.organization_id == organization_id)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.created_at.desc()).offset((p.page - 1) * p.page_size).limit(p.page_size)).all()
    return Page.build([UserOut.model_validate(r) for r in rows], total, p.page, p.page_size)


@router.post("/users", response_model=UserOut, status_code=201, summary="Create a user with any role (administrator)")
def create_user(body: UserCreate, actor: User = Depends(require_permission("user:manage")), db: Session = Depends(get_db)):
    return users_svc.create_user(db, actor, body)


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: uuid.UUID, _: User = Depends(require_permission("user:manage")), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise NotFoundError("User not found")
    return u


@router.patch("/users/{user_id}", response_model=UserOut, summary="Change role / organization / active state / password (administrator)")
def update_user(user_id: uuid.UUID, body: UserUpdate, actor: User = Depends(require_permission("user:manage")), db: Session = Depends(get_db)):
    return users_svc.update_user(db, actor, user_id, body)


@router.post("/organizations", response_model=OrganizationOut, status_code=201, summary="Create an organization (administrator)")
def create_org(body: OrganizationCreate, actor: User = Depends(require_permission("org:manage")), db: Session = Depends(get_db)):
    return users_svc.create_organization(db, actor, body)


@router.get("/organizations", response_model=list[OrganizationOut], summary="Organizations visible to the caller")
def list_orgs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Organization).order_by(Organization.name)
    if user.role != UserRole.ADMIN:
        stmt = stmt.where(Organization.id == user.organization_id)
    return db.scalars(stmt).all()
