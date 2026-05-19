"""Schemas Pydantic de la configuración de usuario (TTS)."""

from pydantic import BaseModel


class UserSettingsSchema(BaseModel):
    tts_speed: float
    tts_volume: float
