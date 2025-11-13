"""add_patient_uuid_map_table

Revision ID: 1f11cb0ff31d
Revises: 0d43dd9516f1
Create Date: 2025-10-27 08:34:05.729291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f11cb0ff31d'
down_revision: Union[str, Sequence[str], None] = '0d43dd9516f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    FASE 1.2: Create patient_uuid_map table for anonymization
    - Stores UUID mapping for manual and excel input
    - Gateway has its own mapping (not stored here)
    """
    op.create_table(
        'patient_uuid_map',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_uuid', sa.String(length=36), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),  # "manual" or "excel"
        sa.Column('source_record_id', sa.String(length=64), nullable=True),
        sa.Column('name_hash', sa.String(length=64), nullable=True),  # SHA256 hash of nama_pasien
        sa.Column('nik_hash', sa.String(length=64), nullable=True),   # SHA256 hash of NIK
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_uuid', name='uq_patient_uuid')
    )
    
    # Indexes for fast lookup
    op.create_index('idx_patient_uuid', 'patient_uuid_map', ['patient_uuid'])
    op.create_index('idx_name_hash', 'patient_uuid_map', ['name_hash'])
    op.create_index('idx_nik_hash', 'patient_uuid_map', ['nik_hash'])
    op.create_index('idx_source_type', 'patient_uuid_map', ['source_type'])


def downgrade() -> None:
    """Drop patient_uuid_map table and indexes."""
    op.drop_index('idx_source_type', table_name='patient_uuid_map')
    op.drop_index('idx_nik_hash', table_name='patient_uuid_map')
    op.drop_index('idx_name_hash', table_name='patient_uuid_map')
    op.drop_index('idx_patient_uuid', table_name='patient_uuid_map')
    op.drop_table('patient_uuid_map')
