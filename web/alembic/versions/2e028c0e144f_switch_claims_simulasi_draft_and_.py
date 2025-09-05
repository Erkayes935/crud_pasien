"""switch claims.simulasi_draft and summary_draft to JSONB

Revision ID: 2e028c0e144f
Revises: 88c41b75f711
Create Date: 2025-09-04 04:36:02.940499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e028c0e144f'
down_revision: Union[str, None] = '88c41b75f711'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
