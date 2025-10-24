"""Merge ed5cb079e2d8 and d2fe5d4add06

Revision ID: ffab9b1af10e
Revises: ed5cb079e2d8, d2fe5d4add06
Create Date: 2025-10-24 08:26:46.889646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffab9b1af10e'
down_revision: Union[str, None] = ('ed5cb079e2d8', 'd2fe5d4add06')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
