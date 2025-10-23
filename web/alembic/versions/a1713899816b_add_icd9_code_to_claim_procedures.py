"""add icd9_code to claim_procedures

Revision ID: a1713899816b
Revises: b2b26d6e262a
Create Date: 2025-10-23 10:18:38.840346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1713899816b'
down_revision: Union[str, None] = 'b2b26d6e262a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "claim_procedures",
        sa.Column("icd9_code", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("claim_procedures", "icd9_code")