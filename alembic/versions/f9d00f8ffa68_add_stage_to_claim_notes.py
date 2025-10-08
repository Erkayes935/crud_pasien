"""add stage to  claim_notes

Revision ID: f9d00f8ffa68
Revises: 7d72f6a7f6ad
Create Date: 2025-10-07 10:54:02.726906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f9d00f8ffa68'
down_revision: Union[str, None] = '7d72f6a7f6ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('claim_notes', sa.Column('stage', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('claim_notes', 'stage')