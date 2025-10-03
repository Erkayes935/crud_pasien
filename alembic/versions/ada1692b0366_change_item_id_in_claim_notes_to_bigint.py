"""change item_id in claim_notes to BIGINT

Revision ID: ada1692b0366
Revises: 7469890e7940
Create Date: 2025-10-03 08:02:50.813117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ada1692b0366'
down_revision: Union[str, None] = '7469890e7940'
branch_labels = None
depends_on = None

def upgrade():
    # ubah kolom item_id jadi BIGINT
    op.alter_column(
        'claim_notes',
        'item_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True
    )

def downgrade():
    # balik lagi ke INTEGER
    op.alter_column(
        'claim_notes',
        'item_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True
    )