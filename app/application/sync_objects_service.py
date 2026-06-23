"""Caso de uso: sincronización de objetos.

Convierte entre los schemas base64 (lo que viaja por JSON) y los bytes
crudos (lo que se guarda en la columna BYTEA), y orquesta el repositorio.
"""

import base64
import binascii

from fastapi import HTTPException, status

from app.infrastructure.repositories.object_repository import ObjectRepository
from app.interfaces.schemas.object_schemas import (
    SavedObjectResponse,
    SavedObjectUpload,
)


class SyncObjectsService:
    def __init__(self, repository: ObjectRepository):
        self.repository = repository

    def upload(
        self, google_user_id: str, objects: list[SavedObjectUpload]
    ) -> int:
        """Guarda/actualiza la lista de objetos del usuario (idempotente).

        Devuelve la cantidad de objetos sincronizados.
        """
        for item in objects:
            try:
                embedding_bytes = base64.b64decode(item.embedding, validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"El campo 'embedding' del objeto '{item.name}' no es base64 válido.",
                )
            try:
                thumbnail_bytes = (
                    base64.b64decode(item.thumbnail, validate=True)
                    if item.thumbnail
                    else None
                )
            except (binascii.Error, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"El campo 'thumbnail' del objeto '{item.name}' no es base64 válido.",
                )
            self.repository.upsert(
                object_id=item.id,
                google_user_id=google_user_id,
                name=item.name,
                embedding=embedding_bytes,
                thumbnail=thumbnail_bytes,
                created_at=item.created_at,
            )
        # Un único commit para toda la tanda.
        self.repository.commit()
        return len(objects)

    def download(self, google_user_id: str) -> list[SavedObjectResponse]:
        """Devuelve todos los objetos del usuario con binarios en base64."""
        rows = self.repository.list_by_user(google_user_id)
        return [
            SavedObjectResponse(
                id=row.id,
                name=row.name,
                embedding=base64.b64encode(row.embedding).decode("ascii"),
                thumbnail=(
                    base64.b64encode(row.thumbnail).decode("ascii")
                    if row.thumbnail
                    else None
                ),
                created_at=row.created_at,
            )
            for row in rows
        ]

    def delete(self, google_user_id: str, object_id: int) -> bool:
        """Elimina un objeto del usuario. False si no existía."""
        return self.repository.delete_for_user(object_id, google_user_id)
