"""add sim_detail to claim_ai_recommendations

Revision ID: cc01f3d99f1a
Revises: 63e12007387a
Create Date: 2025-09-10 13:52:22.833433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc01f3d99f1a'
down_revision: Union[str, None] = '63e12007387a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
