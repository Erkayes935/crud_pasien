"""add field key

Revision ID: 672ba67779c0
Revises: 64088e85bf25
Create Date: 2025-10-07 18:30:09.943194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '672ba67779c0'
down_revision: Union[str, None] = '64088e85bf25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("claim_procedures", sa.Column("icd9_final_by_coder", sa.String(20), nullable=True))
    op.add_column("claim_procedures", sa.Column("verified_by", sa.String(100), nullable=True))
    op.add_column("claim_procedures", sa.Column("verified_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    pass
