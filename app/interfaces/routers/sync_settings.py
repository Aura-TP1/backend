"""Router de sincronización de configuración: /sync/settings y /sync/consent."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.sync_settings_service import SyncSettingsService
from app.infrastructure.database import get_db
from app.infrastructure.repositories.settings_repository import (
    SettingsRepository,
)
from app.interfaces.dependencies import CurrentUser, get_current_user
from app.interfaces.schemas.settings_schemas import (
    ConsentStatusSchema,
    UserSettingsSchema,
)

router = APIRouter(tags=["Sincronización de configuración"])


def _service(db: Session) -> SyncSettingsService:
    return SyncSettingsService(SettingsRepository(db))


@router.get("/sync/settings", response_model=UserSettingsSchema)
def get_settings(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve la configuración del usuario (o valores por defecto)."""
    return _service(db).get(user.google_user_id)


@router.put("/sync/settings", response_model=UserSettingsSchema)
def update_settings(
    data: UserSettingsSchema,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea o actualiza la configuración del usuario autenticado."""
    return _service(db).update(user.google_user_id, data)


@router.get("/sync/consent", response_model=ConsentStatusSchema)
def get_consent(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve el estado de consentimiento del usuario autenticado."""
    return _service(db).get_consent_status(user.google_user_id)


@router.post("/sync/consent", response_model=ConsentStatusSchema)
def give_consent(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra el consentimiento explícito para almacenar objetos personales.

    Requisito previo para poder usar POST /sync/objects/upload.
    """
    return _service(db).give_consent(user.google_user_id)


@router.delete("/sync/consent", response_model=ConsentStatusSchema)
def revoke_consent(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoca el consentimiento. Bloquea futuros uploads hasta volver a aceptarlo.

    No borra los datos ya sincronizados: para eso usar DELETE /sync/account.
    """
    return _service(db).revoke_consent(user.google_user_id)
