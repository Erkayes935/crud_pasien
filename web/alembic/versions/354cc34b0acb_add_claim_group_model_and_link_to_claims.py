"""add claim_group model and link to claims

Revision ID: 354cc34b0acb
Revises: 24e9362f9b59
Create Date: 2025-10-13 14:15:45.161995

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '354cc34b0acb'
down_revision: Union[str, None] = '24e9362f9b59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ✅ Cek dulu apakah tabel sudah ada sebelum create
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "claim_groups" not in tables:
        op.create_table(
            'claim_groups',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('uuid', postgresql.UUID(as_uuid=True), unique=True, nullable=False),
            sa.Column('kode_group', sa.String(length=50), nullable=False, unique=True),
            sa.Column('nama_group', sa.String(length=255), nullable=False),
            sa.Column('deskripsi', sa.Text(), nullable=True),
            sa.Column('tanggal_mulai', sa.Date(), nullable=True),
            sa.Column('tanggal_selesai', sa.Date(), nullable=True),
            sa.Column('patient_id', sa.Integer(), nullable=False),
            sa.Column('hospital_id', sa.Integer(), nullable=True),
            sa.Column('created_by', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'))
        )
    else:
        print("⚠️ Tabel claim_groups sudah ada, dilewati.")

    # ✅ Tambah kolom group_id ke claims jika belum ada
    cols = [c["name"] for c in inspector.get_columns("claims")]
    if "group_id" not in cols:
        op.add_column('claims', sa.Column('group_id', sa.Integer(), nullable=True))
        op.create_foreign_key('fk_claim_group', 'claims', 'claim_groups', ['group_id'], ['id'])
    else:
        print("⚠️ Kolom group_id sudah ada, dilewati.")
