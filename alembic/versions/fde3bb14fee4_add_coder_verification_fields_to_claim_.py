"""add coder verification fields to claim_diagnoses

Revision ID: fde3bb14fee4
Revises: ada1692b0366
Create Date: 2025-10-05 10:17:29.397032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fde3bb14fee4'
down_revision: Union[str, None] = 'ada1692b0366'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('claim_diagnoses', sa.Column('icd10_final_by_coder', sa.String(length=20), nullable=True))
    op.add_column('claim_diagnoses', sa.Column('verified_by', sa.String(length=100), nullable=True))
    op.add_column('claim_diagnoses', sa.Column('verified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('claim_diagnoses', 'verified_at')
    op.drop_column('claim_diagnoses', 'verified_by')
    op.drop_column('claim_diagnoses', 'icd10_final_by_coder')