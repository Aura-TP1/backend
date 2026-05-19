"""Router de sincronización de configuración: /sync/settings."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.sync_settings_service import SyncSettingsService
from app.infrastructure.database import get_db
from app.infrastructure.repositories.settings_repository import (
    SettingsRepository,
)
from app.interfaces.dependencies import CurrentUser, get_current_user
from app.interfaces.schemas.settings_schemas import UserSettingsSchema

router = APIRouter(prefix="/sync/settings", tags=["Sincronización de configuración"])


def _service(db: Session) -> SyncSettingsService:
    return SyncSettingsService(SettingsRepository(db))


@router.get("", response_model=UserSettingsSchema)
def get_settings(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve la configuración del usuario (o valores por defecto)."""
    return _service(db).get(user.google_user_id)


@router.put("", response_model=UserSettingsSchema)
def update_settings(
    data: UserSettingsSchema,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea o actualiza la configuración del usuario autenticado."""
    return _service(db).update(user.google_user_id, data)
