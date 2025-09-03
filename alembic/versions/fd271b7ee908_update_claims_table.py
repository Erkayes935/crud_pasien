"""update claims table

Revision ID: fd271b7ee908
Revises: 09fceb6f05bc
Create Date: 2025-09-04 01:21:11.165816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd271b7ee908'
down_revision: Union[str, None] = '09fceb6f05bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
