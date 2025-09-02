"""update  medical_records table

Revision ID: c88a588f13fa
Revises: b26adba100df
Create Date: 2025-09-01 15:41:27.480964

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c88a588f13fa'
down_revision: Union[str, None] = 'b26adba100df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
