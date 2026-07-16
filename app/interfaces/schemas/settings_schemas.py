"""Schemas Pydantic de la configuración de usuario (TTS) y consentimiento."""

from datetime import datetime

from pydantic import BaseModel


class UserSettingsSchema(BaseModel):
    tts_speed: float
    tts_volume: float


class ConsentStatusSchema(BaseModel):
    """Estado de consentimiento del usuario para almacenar objetos personales."""

    consent_given: bool
    consent_given_at: datetime | None = None
    consent_policy_version: str | None = None
