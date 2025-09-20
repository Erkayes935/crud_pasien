"""create claim_simulations properly

Revision ID: c139a2b8880d
Revises: b4fdee14799c
Create Date: 2025-09-16 02:49:08.551927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c139a2b8880d'
down_revision: Union[str, None] = 'b4fdee14799c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'claim_simulations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('claim_id', sa.Integer, sa.ForeignKey('claims.id')),
        sa.Column('diagnosis_utama_id', sa.Integer, sa.ForeignKey('claim_diagnoses.id')),
        sa.Column('diagnosis_sekunder_id', sa.Integer, sa.ForeignKey('claim_diagnoses.id')),
        sa.Column('procedure_utama_id', sa.Integer, sa.ForeignKey('claim_procedures.id')),
        sa.Column('procedure_sekunder_id', sa.Integer, sa.ForeignKey('claim_procedures.id')),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean, default=False),
        sa.Column('is_dummy', sa.Boolean, default=False),
    )



def downgrade() -> None:
    pass
