"""Router de borrado total de cuenta: /sync/account."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.application.account_service import AccountService
from app.infrastructure.database import get_db
from app.infrastructure.repositories.object_repository import ObjectRepository
from app.infrastructure.repositories.settings_repository import (
    SettingsRepository,
)
from app.interfaces.dependencies import CurrentUser, get_current_user

router = APIRouter(tags=["Cuenta"])


@router.delete("/sync/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Borra permanentemente todos los datos del usuario autenticado:
    objetos guardados (embeddings/thumbnails), configuración y consentimiento.

    No es reversible y no requiere confirmación adicional a nivel API — el
    cliente debe confirmar con el usuario antes de llamar a este endpoint.
    """
    service = AccountService(ObjectRepository(db), SettingsRepository(db))
    service.delete_all_data(user.google_user_id)
