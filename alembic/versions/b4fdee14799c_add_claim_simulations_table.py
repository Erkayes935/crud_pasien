"""add claim_simulations table

Revision ID: b4fdee14799c
Revises: 38eff2430360
Create Date: 2025-09-16 02:32:27.310884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime 


# revision identifiers, used by Alembic.
revision: str = 'b4fdee14799c'
down_revision: Union[str, None] = '38eff2430360'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "claim_simulations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("claim_id", sa.Integer, sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("stage", sa.String, nullable=False),

        sa.Column("diagnosis_utama_id", sa.Integer, sa.ForeignKey("claim_diagnoses.id")),
        sa.Column("diagnosis_sekunder_id", sa.Integer, sa.ForeignKey("claim_diagnoses.id")),

        sa.Column("tindakan_utama_id", sa.Integer, sa.ForeignKey("claim_procedures.id")),
        sa.Column("tindakan_sekunder_id", sa.Integer, sa.ForeignKey("claim_procedures.id")),

        sa.Column("is_dummy", sa.Boolean, server_default="false", nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("claim_simulations")
