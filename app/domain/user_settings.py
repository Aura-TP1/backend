"""Entidad de dominio: UserSettings.

Configuración de Text-To-Speech (TTS) de cada usuario.
Un único registro por usuario, identificado por google_user_id.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserSettings:
    google_user_id: str
    tts_speed: float
    tts_volume: float
    updated_at: datetime
