"""add klinis column to claim_diagnoses

Revision ID: 24e9362f9b59
Revises: 3d26ae2fce3c
Create Date: 2025-10-13 13:58:50.088560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '24e9362f9b59'
down_revision: Union[str, None] = '3d26ae2fce3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'claim_diagnoses',
        sa.Column('klinis', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

def downgrade():
    op.drop_column('claim_diagnoses', 'klinis')