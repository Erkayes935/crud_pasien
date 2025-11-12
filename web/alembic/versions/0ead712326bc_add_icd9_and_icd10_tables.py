"""add icd9 and icd10 tables

Revision ID: 0ead712326bc
Revises: c35d8e2181fe
Create Date: 2025-11-11 16:23:56.100115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = '0ead712326bc'
down_revision: Union[str, None] = 'c35d8e2181fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Tabel ICD9 ===
    op.create_table(
        "icd9",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("code", sa.String(length=10), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True, server_default="ICD-9-CM 2024"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=text("now()"), onupdate=text("now()")),
    )

    # === Tabel ICD10 ===
    op.create_table(
        "icd10",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("code", sa.String(length=10), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True, server_default="ICD-10 2024"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=text("now()"), onupdate=text("now()")),
    )


def downgrade() -> None:
    op.drop_table("icd10")
    op.drop_table("icd9")