"""Repositorio CRUD para la tabla user_settings.

Un único registro por usuario (PK = google_user_id). También guarda el
estado de consentimiento del usuario para almacenar objetos personales.
"""

from datetime import datetime

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

    def set_consent(
        self,
        google_user_id: str,
        *,
        given_at: datetime | None,
        policy_version: str | None,
    ) -> UserSettingsModel:
        """Otorga (given_at != None) o revoca (given_at = None) el consentimiento.

        Crea el registro de settings con valores TTS por defecto si el
        usuario todavía no tenía uno.
        """
        settings = self.get(google_user_id)

        if settings is None:
            settings = UserSettingsModel(
                google_user_id=google_user_id,
                tts_speed=0.85,
                tts_volume=0.8,
                consent_given_at=given_at,
                consent_policy_version=policy_version,
            )
            self.db.add(settings)
        else:
            settings.consent_given_at = given_at
            settings.consent_policy_version = policy_version

        self.db.commit()
        self.db.refresh(settings)
        return settings

    def delete(self, google_user_id: str) -> None:
        """Purga por completo el registro de settings del usuario."""
        self.db.query(UserSettingsModel).filter(
            UserSettingsModel.google_user_id == google_user_id
        ).delete()
