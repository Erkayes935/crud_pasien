"""merge habib

Revision ID: db789688f914
Revises: 63e12007387a
Create Date: 2025-10-08 17:35:15.569182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db789688f914'
down_revision: Union[str, None] = '63e12007387a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ========================
    # 🧠 ClaimDiagnosis
    # ========================
    with op.batch_alter_table('claim_diagnoses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('icd10_final_by_coder', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('verified_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('stage', sa.String(length=50), nullable=True))

    # ========================
    # 💉 ClaimProcedure
    # ========================
    with op.batch_alter_table('claim_procedures', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stage', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('icd9_final_by_coder', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('verified_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('verified_at', sa.DateTime(), nullable=True))

    # ========================
    # 📊 ClaimSimulation
    # ========================
    with op.batch_alter_table('claim_simulations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('coder_icd10_utama', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('coder_icd10_sekunder', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('coder_icd9_utama', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('coder_icd9_sekunder', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('coder_verified_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('coder_verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('coder_note', sa.Text(), nullable=True))

    # ========================
    # 📝 ClaimNote
    # ========================
    op.create_table(
        'claim_notes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column('claim_id', sa.Integer(), sa.ForeignKey('claims.id', ondelete='CASCADE')),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), default=datetime.utcnow),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('claim_notes.id', ondelete='CASCADE'), nullable=True),
        sa.Column('field_key', sa.String(), nullable=True),
        sa.Column('stage', sa.String(), nullable=True)
    )


def downgrade():
    # ⚠️ Hati-hati downgrade, hanya drop kolom tambahan
    with op.batch_alter_table('claim_diagnoses', schema=None) as batch_op:
        for c in ['icd10_final_by_coder', 'verified_by', 'verified_at', 'stage']:
            batch_op.drop_column(c)

    with op.batch_alter_table('claim_procedures', schema=None) as batch_op:
        for c in ['stage', 'icd9_final_by_coder', 'verified_by', 'verified_at']:
            batch_op.drop_column(c)

    with op.batch_alter_table('claim_simulations', schema=None) as batch_op:
        for c in [
            'coder_icd10_utama', 'coder_icd10_sekunder',
            'coder_icd9_utama', 'coder_icd9_sekunder',
            'coder_verified_by', 'coder_verified_at', 'coder_note'
        ]:
            batch_op.drop_column(c)

    op.drop_table('claim_notes')