"""Agrega consentimiento a user_settings y encripta saved_objects.name.

- user_settings: consent_given_at, consent_policy_version.
- saved_objects.name pasa de TEXT a BYTEA porque ahora se guarda encriptado
  con AES-256-GCM (ver app/infrastructure/encryption.py).

ADVERTENCIA: esta migración solo cambia el tipo de columna. Si ya existen
filas con `name` en texto plano, esta migración las convierte a sus bytes
UTF-8 crudos (NO las encripta). En un entorno con datos reales ya
sincronizados hace falta correr un script de backfill que lea cada fila,
encripte el nombre con app.infrastructure.encryption.encrypt() y lo
reescriba antes (o como parte) de este upgrade. En este proyecto no hay
datos de producción todavía, así que no se incluye ese backfill.

Revision ID: 0002_consent_and_encrypted_name
Revises: 0001_initial
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_consent_and_encrypted_name"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column("consent_policy_version", sa.Text(), nullable=True),
    )

    op.alter_column(
        "saved_objects",
        "name",
        type_=sa.LargeBinary(),
        postgresql_using="convert_to(name, 'UTF8')",
    )


def downgrade() -> None:
    op.alter_column(
        "saved_objects",
        "name",
        type_=sa.Text(),
        postgresql_using="convert_from(name, 'UTF8')",
    )
    op.drop_column("user_settings", "consent_policy_version")
    op.drop_column("user_settings", "consent_given_at")
