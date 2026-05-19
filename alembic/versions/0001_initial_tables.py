"""Migración inicial: tablas saved_objects y user_settings.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_objects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("google_user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=False),
        sa.Column("thumbnail", sa.LargeBinary(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Índice para filtrar objetos por usuario.
    op.create_index(
        "ix_saved_objects_google_user_id",
        "saved_objects",
        ["google_user_id"],
    )

    op.create_table(
        "user_settings",
        sa.Column("google_user_id", sa.Text(), nullable=False),
        sa.Column(
            "tts_speed", sa.REAL(), server_default="0.85", nullable=False
        ),
        sa.Column(
            "tts_volume", sa.REAL(), server_default="0.8", nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("google_user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_index(
        "ix_saved_objects_google_user_id", table_name="saved_objects"
    )
    op.drop_table("saved_objects")
