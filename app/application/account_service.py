"""Caso de uso: borrado total de la cuenta del usuario.

Purga saved_objects y user_settings (incluyendo el consentimiento
registrado) del usuario autenticado. No es un soft-delete: los datos se
eliminan de la base de datos en la misma transacción.
"""

from app.infrastructure.repositories.object_repository import ObjectRepository
from app.infrastructure.repositories.settings_repository import (
    SettingsRepository,
)


class AccountService:
    def __init__(
        self, objects: ObjectRepository, settings: SettingsRepository
    ):
        self.objects = objects
        self.settings = settings

    def delete_all_data(self, google_user_id: str) -> None:
        self.objects.delete_all_for_user(google_user_id)
        self.settings.delete(google_user_id)
        self.objects.commit()
