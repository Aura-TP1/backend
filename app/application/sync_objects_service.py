"""Caso de uso: sincronización de objetos.

Convierte entre los schemas base64 (lo que viaja por JSON) y los bytes
crudos (lo que se guarda en la columna BYTEA), encripta/desencripta con
AES-256-GCM (ver app/infrastructure/encryption.py) y orquesta el
repositorio. También aplica límites de tamaño/cantidad para evitar abuso
del endpoint de upload, y exige consentimiento vigente antes de aceptar
datos personales.
"""

import base64
import binascii

from fastapi import HTTPException, status

from app.infrastructure import encryption
from app.infrastructure.repositories.object_repository import ObjectRepository
from app.interfaces.schemas.object_schemas import (
    SavedObjectResponse,
    SavedObjectUpload,
)

# Límites de abuso: los embeddings MobileNetV2 son ~5KB y los thumbnails
# ~15KB (ver app/domain/saved_object.py); se deja margen generoso.
MAX_OBJECTS_PER_UPLOAD = 200
MAX_EMBEDDING_BYTES = 64 * 1024  # 64 KB
MAX_THUMBNAIL_BYTES = 256 * 1024  # 256 KB


class SyncObjectsService:
    def __init__(self, repository: ObjectRepository):
        self.repository = repository

    def upload(
        self,
        google_user_id: str,
        objects: list[SavedObjectUpload],
        *,
        has_consent: bool,
    ) -> int:
        """Guarda/actualiza la lista de objetos del usuario (idempotente).

        Devuelve la cantidad de objetos sincronizados. Requiere que el
        usuario haya dado consentimiento vigente para almacenar sus
        objetos personales (embeddings/thumbnails).
        """
        if not has_consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "El usuario no dio consentimiento vigente para "
                    "sincronizar objetos personales. Llamá a "
                    "POST /sync/consent primero."
                ),
            )

        if len(objects) > MAX_OBJECTS_PER_UPLOAD:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"No se pueden sincronizar más de "
                    f"{MAX_OBJECTS_PER_UPLOAD} objetos en un solo upload."
                ),
            )

        for item in objects:
            try:
                embedding_bytes = base64.b64decode(item.embedding, validate=True)
            except (binascii.Error, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"El campo 'embedding' del objeto '{item.name}' no es base64 válido.",
                )
            if len(embedding_bytes) > MAX_EMBEDDING_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"El embedding del objeto '{item.name}' excede el tamaño máximo permitido.",
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
            if thumbnail_bytes and len(thumbnail_bytes) > MAX_THUMBNAIL_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"El thumbnail del objeto '{item.name}' excede el tamaño máximo permitido.",
                )

            self.repository.upsert(
                object_id=item.id,
                google_user_id=google_user_id,
                name=encryption.encrypt(item.name.encode("utf-8")),
                embedding=encryption.encrypt(embedding_bytes),
                thumbnail=(
                    encryption.encrypt(thumbnail_bytes)
                    if thumbnail_bytes is not None
                    else None
                ),
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
                name=encryption.decrypt(row.name).decode("utf-8"),
                embedding=base64.b64encode(
                    encryption.decrypt(row.embedding)
                ).decode("ascii"),
                thumbnail=(
                    base64.b64encode(encryption.decrypt(row.thumbnail)).decode(
                        "ascii"
                    )
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
