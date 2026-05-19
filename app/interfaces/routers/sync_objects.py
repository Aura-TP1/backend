"""Router de sincronización de objetos: /sync/objects/*."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.sync_objects_service import SyncObjectsService
from app.infrastructure.database import get_db
from app.infrastructure.repositories.object_repository import ObjectRepository
from app.interfaces.dependencies import CurrentUser, get_current_user
from app.interfaces.schemas.object_schemas import (
    SavedObjectResponse,
    SavedObjectUpload,
    UploadResult,
)

router = APIRouter(prefix="/sync/objects", tags=["Sincronización de objetos"])


def _service(db: Session) -> SyncObjectsService:
    return SyncObjectsService(ObjectRepository(db))


@router.post("/upload", response_model=UploadResult)
def upload_objects(
    objects: list[SavedObjectUpload],
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recibe la lista de objetos del móvil y los guarda/actualiza.

    Operación idempotente: si un objeto ya existe (por id) se actualiza,
    si no existe se crea.
    """
    synced = _service(db).upload(user.google_user_id, objects)
    return UploadResult(synced=synced)


@router.get("/download", response_model=list[SavedObjectResponse])
def download_objects(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Devuelve todos los objetos guardados del usuario autenticado."""
    return _service(db).download(user.google_user_id)


@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
    object_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina un objeto específico del usuario autenticado."""
    deleted = _service(db).delete(user.google_user_id, object_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Objeto no encontrado",
        )
