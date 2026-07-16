"""Modelos SQLAlchemy: mapeo de las dos tablas de la base de datos.

- saved_objects: objetos personales guardados por cada usuario.
- user_settings: configuración de TTS y consentimiento por usuario.
"""

from sqlalchemy import Column, DateTime, Integer, LargeBinary, REAL, Text
from sqlalchemy.sql import func

from app.infrastructure.database import Base


class SavedObjectModel(Base):
    __tablename__ = "saved_objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Índice para filtrar rápidamente los objetos de un usuario.
    google_user_id = Column(Text, nullable=False, index=True)
    # Encriptado con AES-256-GCM a nivel aplicación (ver app/infrastructure/encryption.py).
    name = Column(LargeBinary, nullable=False)
    embedding = Column(LargeBinary, nullable=False)  # BYTEA en PostgreSQL, encriptado
    thumbnail = Column(LargeBinary, nullable=True)  # encriptado
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSettingsModel(Base):
    __tablename__ = "user_settings"

    google_user_id = Column(Text, primary_key=True)
    tts_speed = Column(REAL, nullable=False, default=0.85)
    tts_volume = Column(REAL, nullable=False, default=0.8)
    # Consentimiento explícito para almacenar objetos personales (embeddings/
    # thumbnails). Null = el usuario nunca dio consentimiento.
    consent_given_at = Column(DateTime(timezone=True), nullable=True)
    consent_policy_version = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
