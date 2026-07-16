"""Repositorio CRUD para la tabla saved_objects.

Encapsula todo el acceso a base de datos de los objetos guardados.
Siempre filtra por google_user_id para que un usuario solo toque sus datos.
"""

from sqlalchemy.orm import Session

from app.infrastructure.models import SavedObjectModel


class ObjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_user(self, google_user_id: str) -> list[SavedObjectModel]:
        return (
            self.db.query(SavedObjectModel)
            .filter(SavedObjectModel.google_user_id == google_user_id)
            .all()
        )

    def get_for_user(
        self, object_id: int, google_user_id: str
    ) -> SavedObjectModel | None:
        return (
            self.db.query(SavedObjectModel)
            .filter(
                SavedObjectModel.id == object_id,
                SavedObjectModel.google_user_id == google_user_id,
            )
            .first()
        )

    def upsert(
        self,
        *,
        object_id: int,
        google_user_id: str,
        name: bytes,
        embedding: bytes,
        thumbnail: bytes | None,
        created_at,
    ) -> SavedObjectModel:
        """Idempotente: si el objeto existe para el usuario lo actualiza,
        si no existe lo crea."""
        obj = self.get_for_user(object_id, google_user_id)

        if obj is None:
            obj = SavedObjectModel(
                id=object_id,
                google_user_id=google_user_id,
                name=name,
                embedding=embedding,
                thumbnail=thumbnail,
                created_at=created_at,
            )
            self.db.add(obj)
        else:
            obj.name = name
            obj.embedding = embedding
            obj.thumbnail = thumbnail
            obj.created_at = created_at

        return obj

    def delete_for_user(self, object_id: int, google_user_id: str) -> bool:
        """Devuelve True si se eliminó, False si el objeto no existía."""
        obj = self.get_for_user(object_id, google_user_id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True

    def delete_all_for_user(self, google_user_id: str) -> None:
        """Purga todos los objetos del usuario (borrado total de cuenta)."""
        self.db.query(SavedObjectModel).filter(
            SavedObjectModel.google_user_id == google_user_id
        ).delete()

    def commit(self) -> None:
        self.db.commit()
