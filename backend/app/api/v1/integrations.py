from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models import User
from app.schemas.integration import ConnectRequest, IntegrationItem, IntegrationList, SyncRequest, SyncResult, TestResult
from app.services import integrations as svc

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("", response_model=IntegrationList,
            summary="Provider catalog merged with stored config. Secret values are never returned (secrets echo as ••••).")
def list_(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.list_integrations(db, user)


@router.get("/{key}", response_model=IntegrationItem, summary="One provider + stored configuration (never secrets)")
def get(key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.get_item(db, user, key)


@router.post("/{key}/connect", response_model=IntegrationItem,
             summary="Validate + encrypt (Fernet) the configuration and mark the provider 'configured'")
def connect(key: str, body: ConnectRequest, user: User = Depends(require_permission("connector:run")), db: Session = Depends(get_db)):
    return svc.connect(db, user, key, body.config)


@router.post("/{key}/disconnect", response_model=IntegrationItem, summary="Remove the stored configuration (back to 'not_configured')")
def disconnect(key: str, user: User = Depends(require_permission("connector:run")), db: Session = Depends(get_db)):
    return svc.disconnect(db, user, key)


@router.post("/{key}/test", response_model=TestResult,
             summary="Honest connectivity test: real DNS/HTTP checks where possible; credential providers report 'unverified' rather than fake success")
def test(key: str, user: User = Depends(require_permission("connector:run")), db: Session = Depends(get_db)):
    return svc.test_provider(db, user, key)


@router.post("/{key}/sync", response_model=SyncResult,
             summary="Run the matching sample connector (synthetic data) for a configured provider; 400 no_connector_available otherwise")
def sync(key: str, body: SyncRequest | None = None, user: User = Depends(require_permission("connector:run")), db: Session = Depends(get_db)):
    body = body or SyncRequest()
    return svc.sync(db, user, key, body.brand_id, body.query)
