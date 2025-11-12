"""move aspek_lainnya to claim_procedure_details

Revision ID: c35d8e2181fe
Revises: f5a5a35b07bf
Create Date: 2025-11-08 11:06:06.831125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c35d8e2181fe'
down_revision: Union[str, None] = 'f5a5a35b07bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('claim_procedure_details', sa.Column('aspek_lainnya', sa.Text(), nullable=True))
    op.drop_column('claim_procedures', 'aspek_lainnya')

def downgrade() -> None:
    op.add_column('claim_procedures', sa.Column('aspek_lainnya', sa.Text(), nullable=True))
    op.drop_column('claim_procedure_details', 'aspek_lainnya')
