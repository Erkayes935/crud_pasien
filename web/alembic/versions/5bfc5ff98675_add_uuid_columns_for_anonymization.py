"""add_uuid_columns_for_anonymization

Revision ID: 5bfc5ff98675
Revises: c88a588f13fa
Create Date: 2025-09-02 17:42:22.956211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bfc5ff98675'
down_revision: Union[str, None] = 'c88a588f13fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
