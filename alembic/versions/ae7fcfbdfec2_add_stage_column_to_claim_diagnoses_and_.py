"""add stage column to claim_diagnoses and claim_procedures

Revision ID: ae7fcfbdfec2
Revises: 672ba67779c0
Create Date: 2025-10-08 07:27:34.932041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae7fcfbdfec2'
down_revision: Union[str, None] = '672ba67779c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.add_column(
        "claim_diagnoses",
        sa.Column("stage", sa.String(50), nullable=False, server_default="admission")
    )
    op.add_column(
        "claim_procedures",
        sa.Column("stage", sa.String(50), nullable=False, server_default="admission")
    )

def downgrade():
    op.drop_column("claim_diagnoses", "stage")
    op.drop_column("claim_procedures", "stage")