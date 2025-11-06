"""merge multiple heads before claim list indexes

Revision ID: 5db13cf46f42
Revises: 02f582a10162, f26f3346cb7e
Create Date: 2025-10-26 10:42:27.457190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5db13cf46f42'
down_revision: Union[str, None] = ('02f582a10162', 'f26f3346cb7e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
