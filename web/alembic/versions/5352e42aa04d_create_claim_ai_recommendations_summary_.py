"""create claim_ai_recommendations_summary table

Revision ID: 5352e42aa04d
Revises: c88a588f13fa
Create Date: 2025-09-03 09:50:09.717504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5352e42aa04d'
down_revision: Union[str, None] = 'c88a588f13fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
