"""make medical_record_id nullable

Revision ID: e0b00c390d53
Revises: db789688f914
Create Date: 2025-10-10 23:52:38.675208

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e0b00c390d53'
down_revision: Union[str, None] = 'db789688f914'
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
