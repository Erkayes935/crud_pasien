"""create inacbg_tariff table

Revision ID: create_inacbg_tariff
Revises: 
Create Date: 2025-11-07 10:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_inacbg_tariff'
down_revision: Union[str, None] = '79524eb7ddb5'  # Current head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabel tarif INA-CBG
    op.create_table(
        'inacbg_tariff',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kode_cbg', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('deskripsi', sa.Text(), nullable=True),
        sa.Column('tarif_kelas_1', sa.BigInteger(), nullable=True),
        sa.Column('tarif_kelas_2', sa.BigInteger(), nullable=True),
        sa.Column('tarif_kelas_3', sa.BigInteger(), nullable=True),
        sa.Column('tarif', sa.BigInteger(), nullable=True),
        sa.Column('regional', sa.String(10), nullable=True),
        sa.Column('kelas_rs', sa.String(10), nullable=True),
        sa.Column('tipe_rs', sa.String(50), nullable=True),
        sa.Column('layanan', sa.String(50), nullable=True),
        sa.Column('no', sa.Integer(), nullable=True),
        sa.Column('page_number_pdf', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Index untuk query cepat
    op.create_index('idx_kode_cbg', 'inacbg_tariff', ['kode_cbg'])
    op.create_index('idx_kelas_regional', 'inacbg_tariff', ['kelas_rs', 'regional'])


def downgrade() -> None:
    op.drop_index('idx_kelas_regional', table_name='inacbg_tariff')
    op.drop_index('idx_kode_cbg', table_name='inacbg_tariff')
    op.drop_table('inacbg_tariff')
