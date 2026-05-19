"""Schemas Pydantic de los objetos guardados.

Los campos binarios (embedding, thumbnail) viajan como texto base64
dentro del JSON para mantener compatibilidad con el cliente Flutter.
"""

from datetime import datetime

from pydantic import BaseModel


class SavedObjectUpload(BaseModel):
    """Objeto que el móvil envía al backend en el upload."""

    id: int
    name: str
    embedding: str  # base64 del vector de embedding
    thumbnail: str | None = None  # base64 del JPEG, opcional
    created_at: datetime


class SavedObjectResponse(BaseModel):
    """Objeto que el backend devuelve al móvil en el download."""

    id: int
    name: str
    embedding: str  # base64 del vector de embedding
    thumbnail: str | None = None  # base64 del JPEG, opcional
    created_at: datetime


class UploadResult(BaseModel):
    """Resumen devuelto tras un upload de varios objetos."""

    synced: int
