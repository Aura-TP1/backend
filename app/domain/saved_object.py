"""Entidad de dominio: SavedObject.

Representa un objeto personal que el usuario guardó en la app AURA.
Es un objeto puro de negocio, sin dependencias de SQLAlchemy ni FastAPI.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SavedObject:
    id: int
    google_user_id: str
    name: str
    embedding: bytes  # vector de 1280 floats serializado (~5120 bytes)
    thumbnail: bytes | None  # imagen JPEG 100x100px (~15KB), opcional
    created_at: datetime
