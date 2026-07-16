"""Entidad de dominio: UserSettings.

Configuración de Text-To-Speech (TTS) y consentimiento de cada usuario.
Un único registro por usuario, identificado por google_user_id.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserSettings:
    google_user_id: str
    tts_speed: float
    tts_volume: float
    consent_given_at: datetime | None
    consent_policy_version: str | None
    updated_at: datetime
