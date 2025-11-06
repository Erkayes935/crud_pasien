"""Merge a1713899816b and ffab9b1af10e

Revision ID: 02f582a10162
Revises: a1713899816b, ffab9b1af10e
Create Date: 2025-10-24 08:31:19.414148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02f582a10162'
down_revision: Union[str, None] = ('a1713899816b', 'ffab9b1af10e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
