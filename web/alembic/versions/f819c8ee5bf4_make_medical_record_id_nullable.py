"""make medical_record_id nullable

Revision ID: f819c8ee5bf4
Revises: e0b00c390d53
Create Date: 2025-10-11 00:01:02.849600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f819c8ee5bf4'
down_revision: Union[str, None] = 'e0b00c390d53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.alter_column(
        'claims',
        'medical_record_id',
        existing_type=sa.INTEGER(),
        nullable=True
    )

def downgrade():
    op.alter_column(
        'claims',
        'medical_record_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )