"""Repositorio CRUD para la tabla user_settings.

Un único registro por usuario (PK = google_user_id).
"""

from sqlalchemy.orm import Session

from app.infrastructure.models import UserSettingsModel


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, google_user_id: str) -> UserSettingsModel | None:
        return (
            self.db.query(UserSettingsModel)
            .filter(UserSettingsModel.google_user_id == google_user_id)
            .first()
        )

    def upsert(
        self, google_user_id: str, tts_speed: float, tts_volume: float
    ) -> UserSettingsModel:
        """Idempotente: crea el registro del usuario o actualiza el existente."""
        settings = self.get(google_user_id)

        if settings is None:
            settings = UserSettingsModel(
                google_user_id=google_user_id,
                tts_speed=tts_speed,
                tts_volume=tts_volume,
            )
            self.db.add(settings)
        else:
            settings.tts_speed = tts_speed
            settings.tts_volume = tts_volume

        self.db.commit()
        self.db.refresh(settings)
        return settings
