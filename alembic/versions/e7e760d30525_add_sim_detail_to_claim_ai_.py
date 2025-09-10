"""add sim_detail to claim_ai_recommendations

Revision ID: e7e760d30525
Revises: cc01f3d99f1a
Create Date: 2025-09-10 13:57:36.434245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7e760d30525'
down_revision: Union[str, None] = 'cc01f3d99f1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'claim_ai_recommendations',
        sa.Column('sim_detail', postgresql.JSONB, nullable=True)
    )


def downgrade() -> None:
    op.drop_column('claim_ai_recommendations', 'sim_detail')
