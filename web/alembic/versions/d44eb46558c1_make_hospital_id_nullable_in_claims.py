"""make hospital_id nullable in claims

Revision ID: d44eb46558c1
Revises: b50311bfbba7
Create Date: 2025-10-11 14:45:36.963096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd44eb46558c1'
down_revision: Union[str, None] = 'b50311bfbba7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # ubah kolom hospital_id di tabel claims agar nullable
    op.alter_column(
        'claims',
        'hospital_id',
        existing_type=sa.Integer(),
        nullable=True
    )


def downgrade():
    # revert perubahan (kembali ke NOT NULL)
    op.alter_column(
        'claims',
        'hospital_id',
        existing_type=sa.Integer(),
        nullable=False
    )