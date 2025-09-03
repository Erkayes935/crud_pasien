"""add subtype column to claim_diagnoses

Revision ID: fix_claim_diagnosis_subtype
Revises: <isi_dengan_down_revision_terakhir>
Create Date: 2025-09-03
"""

# Alembic identifiers
revision = 'fix_claim_diagnosis_subtype'
down_revision = '4071d1628a18'
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa

def upgrade():
    with op.batch_alter_table('claim_diagnoses') as batch_op:
        batch_op.add_column(sa.Column('subtype', sa.String(length=50), nullable=True))

def downgrade():
    with op.batch_alter_table('claim_diagnoses') as batch_op:
        batch_op.drop_column('subtype')
