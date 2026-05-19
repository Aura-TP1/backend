"""Caso de uso: sincronización de configuración (TTS) del usuario."""

from app.infrastructure.repositories.settings_repository import (
    SettingsRepository,
)
from app.interfaces.schemas.settings_schemas import UserSettingsSchema

# Valores por defecto si el usuario aún no guardó configuración.
DEFAULT_TTS_SPEED = 0.85
DEFAULT_TTS_VOLUME = 0.8


class SyncSettingsService:
    def __init__(self, repository: SettingsRepository):
        self.repository = repository

    def get(self, google_user_id: str) -> UserSettingsSchema:
        """Devuelve la configuración del usuario o los valores por defecto."""
        settings = self.repository.get(google_user_id)
        if settings is None:
            return UserSettingsSchema(
                tts_speed=DEFAULT_TTS_SPEED,
                tts_volume=DEFAULT_TTS_VOLUME,
            )
        return UserSettingsSchema(
            tts_speed=settings.tts_speed,
            tts_volume=settings.tts_volume,
        )

    def update(
        self, google_user_id: str, data: UserSettingsSchema
    ) -> UserSettingsSchema:
        """Crea o actualiza la configuración del usuario."""
        settings = self.repository.upsert(
            google_user_id=google_user_id,
            tts_speed=data.tts_speed,
            tts_volume=data.tts_volume,
        )
        return UserSettingsSchema(
            tts_speed=settings.tts_speed,
            tts_volume=settings.tts_volume,
        )
