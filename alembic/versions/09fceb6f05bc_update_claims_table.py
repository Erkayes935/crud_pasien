"""update claims table

Revision ID: 09fceb6f05bc
Revises: 5352e42aa04d
Create Date: 2025-09-04 01:00:07.159330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09fceb6f05bc'
down_revision: Union[str, None] = '5352e42aa04d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
