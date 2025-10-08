"""Add field_key and stage to claim_notes

Revision ID: 64088e85bf25
Revises: f9d00f8ffa68
Create Date: 2025-10-07 16:53:24.983828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64088e85bf25'
down_revision: Union[str, None] = 'f9d00f8ffa68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('claim_notes', sa.Column('field_key', sa.String(), nullable=True))

def downgrade():
    op.drop_column('claim_notes', 'field_key')