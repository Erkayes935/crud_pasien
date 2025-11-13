"""add aspek_lainnya json field to diagnosis, procedure, combo

Revision ID: f5a5a35b07bf
Revises: fix_inacbg_composite
Create Date: 2025-11-08 09:06:12.712393

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a5a35b07bf'
down_revision: Union[str, None] = 'fix_inacbg_composite'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('claim_diagnoses', sa.Column('aspek_lainnya', sa.Text(), nullable=True))
    op.add_column('claim_procedures', sa.Column('aspek_lainnya', sa.Text(), nullable=True))
    op.create_table(
        'claim_combo_evaluations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('claim_id', sa.Integer(), sa.ForeignKey('claims.id'), nullable=False),
        sa.Column('aspek_lainnya', sa.Text(), nullable=True),
    )

def downgrade():
    op.drop_column('claim_diagnoses', 'aspek_lainnya')
    op.drop_column('claim_procedures', 'aspek_lainnya')
    op.drop_table('claim_combo_evaluations')

