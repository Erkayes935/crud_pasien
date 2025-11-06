"""drop claim_simulation_id from claim_procedure_details

Revision ID: 5d43427dcd21
Revises: 98015e9146f7
Create Date: 2025-11-05 06:50:42.666500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d43427dcd21'
down_revision: Union[str, None] = '98015e9146f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 🩹 Hapus kolom claim_simulation_id kalau masih ada
    with op.batch_alter_table("claim_procedure_details") as batch_op:
        batch_op.drop_column("claim_simulation_id")


def downgrade() -> None:
    # 🔄 Tambahkan kembali kalau downgrade
    with op.batch_alter_table("claim_procedure_details") as batch_op:
        batch_op.add_column(sa.Column("claim_simulation_id", sa.Integer(), nullable=True))
