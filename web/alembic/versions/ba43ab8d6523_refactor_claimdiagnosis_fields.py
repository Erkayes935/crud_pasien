"""refactor ClaimDiagnosis fields

Revision ID: ba43ab8d6523
Revises: 45511341b74a
Create Date: 2025-10-20 16:17:46.209547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ba43ab8d6523'
down_revision: Union[str, None] = '45511341b74a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # rename kolom lama
    with op.batch_alter_table('claim_diagnoses', schema=None) as batch_op:
        batch_op.alter_column('justifikasi', new_column_name='justifikasi_klinis')
        batch_op.alter_column('kode_ganda', new_column_name='kode_ganda_icd10')
        batch_op.alter_column('z_code', new_column_name='z_code_icd10')
        batch_op.alter_column('kode_bpjs_khusus', new_column_name='kode_bpjs_khusus_icd10')

        # hapus kolom lama yang sudah tidak dipakai
        batch_op.drop_column('struktur_icd10')
        batch_op.drop_column('syarat')
        batch_op.drop_column('kelayakan')
        batch_op.drop_column('perpanjangan')
        batch_op.drop_column('kesesuaian_rs')

        # tambah kolom baru
        batch_op.add_column(sa.Column('tingkat_faskes', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('justifikasi_faskes', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('kompetensi_faskes', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('lama_rawat_inap', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('kriteria_rawat_inap', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('indikasi_rawat_inap', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('indikasi_rujukan', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('kriteria_rujukan', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('tujuan_rujukan', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('claim_diagnoses', schema=None) as batch_op:
        # balikin kolom baru
        batch_op.drop_column('tingkat_faskes')
        batch_op.drop_column('justifikasi_faskes')
        batch_op.drop_column('kompetensi_faskes')
        batch_op.drop_column('lama_rawat_inap')
        batch_op.drop_column('kriteria_rawat_inap')
        batch_op.drop_column('indikasi_rawat_inap')
        batch_op.drop_column('indikasi_rujukan')
        batch_op.drop_column('kriteria_rujukan')
        batch_op.drop_column('tujuan_rujukan')

        # tambahkan kembali kolom lama
        batch_op.add_column(sa.Column('struktur_icd10', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('syarat', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('kelayakan', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('perpanjangan', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('kesesuaian_rs', sa.Text(), nullable=True))

        # rename balik kolom
        batch_op.alter_column('justifikasi_klinis', new_column_name='justifikasi')
        batch_op.alter_column('kode_ganda_icd10', new_column_name='kode_ganda')
        batch_op.alter_column('z_code_icd10', new_column_name='z_code')
        batch_op.alter_column('kode_bpjs_khusus_icd10', new_column_name='kode_bpjs_khusus')
