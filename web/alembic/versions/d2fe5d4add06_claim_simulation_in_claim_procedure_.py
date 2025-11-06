"""claim_simulation in claim procedure_detail

Revision ID: d2fe5d4add06
Revises: a1713899816b
Create Date: 2025-10-24 08:21:09.111940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2fe5d4add06'
down_revision: Union[str, None] = 'ed5cb079e2d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Tambahkan kolom claim_simulation_id ke tabel claim_procedure_details
    op.add_column(
        'claim_procedure_details',
        sa.Column('claim_simulation_id', sa.Integer(), nullable=True)
    )

    # Tambahkan foreign key ke claim_simulations.id
    op.create_foreign_key(
        'fk_claim_procedure_details_claim_simulation_id',
        'claim_procedure_details',
        'claim_simulations',
        ['claim_simulation_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Setelah FK dibuat, ubah kolom jadi NOT NULL (opsional — hanya kalau datanya sudah siap)
    # op.alter_column('claim_procedure_details', 'claim_simulation_id', nullable=False)


def downgrade():
    # Hapus foreign key dan kolom
    op.drop_constraint('fk_claim_procedure_details_claim_simulation_id', 'claim_procedure_details', type_='foreignkey')
    op.drop_column('claim_procedure_details', 'claim_simulation_id')