"""Remove unused columns in claim_procedure_evaluations

Revision ID: f26f3346cb7e
Revises: 5843332e77ee
Create Date: 2025-10-24 14:03:53.602583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f26f3346cb7e'
down_revision: Union[str, None] = '5843332e77ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 🔹 1. Drop semua kolom lama yang sudah tidak digunakan
    drop_cols = [
        "validitas",
        "validitas_detail",
        "status_tindakan",
        "tarif_impact",
        "faskes",
        "rawat_inap",
        "syarat_klinis",
    ]
    for col in drop_cols:
        try:
            op.drop_column("claim_procedure_evaluations", col)
            print(f"✅ dropped column: {col}")
        except Exception:
            print(f"⚠️ column {col} not found or already dropped")

    # 🔹 2. Tambahkan kolom baru (jaga-jaga kalau belum ada)
    new_cols = [
        sa.Column("wajib", sa.Text(), nullable=True),
        sa.Column("validasi", sa.Text(), nullable=True),
        sa.Column("dampak", sa.Text(), nullable=True),
        sa.Column("konflik", sa.Text(), nullable=True),
    ]
    for col in new_cols:
        try:
            op.add_column("claim_procedure_evaluations", col)
            print(f"✅ added column: {col.name}")
        except Exception:
            print(f"⚠️ column {col.name} already exists")


def downgrade():
    # 🔹 1. Tambahkan kembali kolom lama (restore)
    op.add_column("claim_procedure_evaluations", sa.Column("validitas", sa.String(length=50), nullable=True))
    op.add_column("claim_procedure_evaluations", sa.Column("validitas_detail", sa.Text(), nullable=True))
    op.add_column("claim_procedure_evaluations", sa.Column("status_tindakan", sa.Text(), nullable=True))
    op.add_column("claim_procedure_evaluations", sa.Column("tarif_impact", sa.Numeric(18, 2), nullable=True))
    op.add_column("claim_procedure_evaluations", sa.Column("faskes", sa.Text(), nullable=True))
    op.add_column("claim_procedure_evaluations", sa.Column("rawat_inap", sa.Text(), nullable=True))
    op.add_column("claim_procedure_evaluations", sa.Column("syarat_klinis", sa.Text(), nullable=True))

    # 🔹 2. Hapus kolom baru (rollback)
    for col in ["wajib", "validasi", "dampak", "konflik"]:
        try:
            op.drop_column("claim_procedure_evaluations", col)
        except Exception:
            print(f"⚠️ rollback: column {col} not found")
