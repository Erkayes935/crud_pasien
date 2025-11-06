"""Change severity column to Text in claim_diagnosis_evaluations

Revision ID: b7b8fa304555
Revises: 387475cdff47
Create Date: 2025-10-24 12:05:26.389271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7b8fa304555'
down_revision: Union[str, None] = '387475cdff47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    op.alter_column(
        "claim_diagnosis_evaluations",
        "severity",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True
    )

def downgrade():
    op.alter_column(
        "claim_diagnosis_evaluations",
        "severity",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True
    )
