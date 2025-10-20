"""add diagnosis_source to claim_diagnoses and rename procedure_type to procedure_source to claim_procedures

Revision ID: 45511341b74a
Revises: 1b40ebb3f795
Create Date: 2025-10-20 07:21:36.360126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '45511341b74a'
down_revision: Union[str, None] = '1b40ebb3f795'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ rename procedure_type → procedure_source
    with op.batch_alter_table('claim_procedures', schema=None) as batch_op:
        batch_op.alter_column('procedure_type', new_column_name='procedure_source')

    # 2️⃣ tambahkan diagnosis_source di claim_diagnoses
    op.add_column('claim_diagnoses',
        sa.Column('diagnosis_source', sa.String(length=50), nullable=False, server_default='manual')
    )


def downgrade() -> None:
    # rollback kalau perlu
    with op.batch_alter_table('claim_procedures', schema=None) as batch_op:
        batch_op.alter_column('procedure_source', new_column_name='procedure_type')

    op.drop_column('claim_diagnoses', 'diagnosis_source')