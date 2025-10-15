"""add origin_item null in claimnote

Revision ID: 0242f5008e2a
Revises: f819c8ee5bf4
Create Date: 2025-10-11 08:47:31.790133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0242f5008e2a'
down_revision: Union[str, None] = 'f819c8ee5bf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Tambahkan kolom origin_item_id
    op.add_column(
        'claim_notes',
        sa.Column('origin_item_id', sa.Integer(), nullable=True)
    )

    # Optional: index agar pencarian lebih cepat
    op.create_index(
        'ix_claim_notes_origin_item_id',
        'claim_notes',
        ['origin_item_id']
    )

    print("✅ Column 'origin_item_id' successfully added to claim_notes.")


def downgrade():
    # Hapus index dan kolom jika rollback
    op.drop_index('ix_claim_notes_origin_item_id', table_name='claim_notes')
    op.drop_column('claim_notes', 'origin_item_id')

    print("⏪ Column 'origin_item_id' removed from claim_notes.")