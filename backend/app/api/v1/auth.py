from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services import users as users_svc

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit("register", "register_rate_limit_per_minute"))],
             summary="Self-register (brand_owner role, no organization until an administrator assigns one)")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    return users_svc.register_public(db, body.email, body.full_name, body.password)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("login", "login_rate_limit_per_minute"))], summary="Login with JSON credentials")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    token, expires = users_svc.authenticate(db, body.email, body.password)
    return TokenResponse(access_token=token, expires_in=expires)


@router.post("/token", response_model=TokenResponse, dependencies=[Depends(rate_limit("login", "login_rate_limit_per_minute"))], summary="OAuth2 password form (used by Swagger 'Authorize')")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    token, expires = users_svc.authenticate(db, form.username, form.password)
    return TokenResponse(access_token=token, expires_in=expires)


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)):
    return user
