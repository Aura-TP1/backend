"""Caso de uso: sincronización de configuración (TTS) y consentimiento."""

from datetime import datetime, timezone

from app.infrastructure.repositories.settings_repository import (
    SettingsRepository,
)
from app.interfaces.schemas.settings_schemas import (
    ConsentStatusSchema,
    UserSettingsSchema,
)

# Valores por defecto si el usuario aún no guardó configuración.
DEFAULT_TTS_SPEED = 0.85
DEFAULT_TTS_VOLUME = 0.8

# Versión vigente de la política de privacidad/consentimiento. Subirla
# invalida el consentimiento previo de todos los usuarios (deja de coincidir
# con consent_policy_version) y los obliga a volver a aceptar.
CURRENT_CONSENT_POLICY_VERSION = "1.0"


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

    def has_valid_consent(self, google_user_id: str) -> bool:
        """True si el usuario dio consentimiento para la política vigente."""
        settings = self.repository.get(google_user_id)
        return bool(
            settings
            and settings.consent_given_at is not None
            and settings.consent_policy_version == CURRENT_CONSENT_POLICY_VERSION
        )

    def get_consent_status(self, google_user_id: str) -> ConsentStatusSchema:
        settings = self.repository.get(google_user_id)
        if settings is None or settings.consent_given_at is None:
            return ConsentStatusSchema(consent_given=False)
        return ConsentStatusSchema(
            consent_given=(
                settings.consent_policy_version == CURRENT_CONSENT_POLICY_VERSION
            ),
            consent_given_at=settings.consent_given_at,
            consent_policy_version=settings.consent_policy_version,
        )

    def give_consent(self, google_user_id: str) -> ConsentStatusSchema:
        """Registra el consentimiento explícito del usuario para la política vigente."""
        settings = self.repository.set_consent(
            google_user_id,
            given_at=datetime.now(timezone.utc),
            policy_version=CURRENT_CONSENT_POLICY_VERSION,
        )
        return ConsentStatusSchema(
            consent_given=True,
            consent_given_at=settings.consent_given_at,
            consent_policy_version=settings.consent_policy_version,
        )

    def revoke_consent(self, google_user_id: str) -> ConsentStatusSchema:
        """Revoca el consentimiento. Los uploads futuros quedarán bloqueados."""
        self.repository.set_consent(google_user_id, given_at=None, policy_version=None)
        return ConsentStatusSchema(consent_given=False)
