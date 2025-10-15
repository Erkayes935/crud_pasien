"""add description to claim_tariffs

Revision ID: 1b40ebb3f795
Revises: 896385aebcf7
Create Date: 2025-10-15 13:41:07.501431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1b40ebb3f795'
down_revision: Union[str, None] = '896385aebcf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('claim_tariffs', sa.Column('description', sa.Text(), nullable=True))
def downgrade():
    op.drop_column('claim_tariffs', 'description')
