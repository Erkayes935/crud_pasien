"""add coder verification fields to claim_simulations

Revision ID: 529a547aaf7d
Revises: fde3bb14fee4
Create Date: 2025-10-05 12:08:41.287823

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '529a547aaf7d'
down_revision: Union[str, None] = 'fde3bb14fee4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "claim_simulations",
        sa.Column("coder_icd10_utama", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "claim_simulations",
        sa.Column("coder_icd10_sekunder", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "claim_simulations",
        sa.Column("coder_verified_by", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "claim_simulations",
        sa.Column("coder_verified_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "claim_simulations",
        sa.Column("coder_note", sa.Text(), nullable=True),
    )

    # indeks opsional untuk performa query
    op.create_index(
        "ix_claim_simulations_claim_id", "claim_simulations", ["claim_id"], unique=False
    )
    op.create_index(
        "ix_claim_simulations_stage", "claim_simulations", ["stage"], unique=False
    )


def downgrade() -> None:
    # drop index jika dibuat di upgrade
    op.drop_index("ix_claim_simulations_stage", table_name="claim_simulations")
    op.drop_index("ix_claim_simulations_claim_id", table_name="claim_simulations")

    # drop kolom-kolom baru
    op.drop_column("claim_simulations", "coder_note")
    op.drop_column("claim_simulations", "coder_verified_at")
    op.drop_column("claim_simulations", "coder_verified_by")
    op.drop_column("claim_simulations", "coder_icd10_sekunder")
    op.drop_column("claim_simulations", "coder_icd10_utama")