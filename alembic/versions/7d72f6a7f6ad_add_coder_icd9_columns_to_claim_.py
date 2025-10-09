"""add coder_icd9 columns to claim_simulations

Revision ID: 7d72f6a7f6ad
Revises: 529a547aaf7d
Create Date: 2025-10-07 09:57:38.786818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7d72f6a7f6ad'
down_revision: Union[str, None] = '529a547aaf7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tambahkan hanya kolom baru yang kamu inginkan
    op.add_column('claim_simulations', sa.Column('coder_icd9_utama', sa.String(length=20), nullable=True))
    op.add_column('claim_simulations', sa.Column('coder_icd9_sekunder', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('claim_simulations', 'coder_icd9_sekunder')
    op.drop_column('claim_simulations', 'coder_icd9_utama')
