"""add sim_detail to claim_ai_recommendations

Revision ID: 8fbc7184b1f2
Revises: e7e760d30525
Create Date: 2025-09-10 14:04:16.228338

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '8fbc7184b1f2'
down_revision: Union[str, None] = 'e7e760d30525'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claim_ai_recommendations', sa.Column('sim_detail', postgresql.JSONB, nullable=True))


def downgrade() -> None:
    pass
