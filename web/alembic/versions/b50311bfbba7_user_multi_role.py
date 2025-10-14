"""user multi role

Revision ID: b50311bfbba7
Revises: 952037d3c640
Create Date: 2025-10-11 11:30:51.938148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = 'b50311bfbba7'
down_revision: Union[str, None] = '952037d3c640'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    # ====== 1️⃣ Buat tabel roles ======
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(length=50), unique=True, nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
    )

    # ====== 2️⃣ Buat tabel user_roles (bridge) ======
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

    # ❗ Tidak menghapus kolom "role" lama di tabel users — biarkan tetap ada
    # supaya sistem lama yang masih baca user.role tetap berjalan

    # ====== 3️⃣ Seeder role default ======
    conn = op.get_bind()
    role_table = table('roles',
        column('name', sa.String),
        column('description', sa.String),
        column('is_active', sa.Boolean),
        column('created_at', sa.DateTime)
    )

    default_roles = [
        ("doctor", "Peran dokter yang membuat dan mengedit klaim"),
        ("coder", "Peran coder yang memverifikasi ICD dan i-DRG"),
        ("verifikator", "Peran verifikator internal RS"),
        ("admin_rs", "Admin rumah sakit yang mengelola user"),
        ("superadmin", "Super admin sistem pusat"),
        ("validator", "Validator eksternal klaim"),
        ("manajemen", "Manajemen rumah sakit (read-only dashboard)"),
        ("costing", "Tim costing dan analisa tarif"),
    ]

    conn.execute(
        role_table.insert(),
        [{"name": n, "description": d, "is_active": True, "created_at": datetime.utcnow()} for n, d in default_roles]
    )


def downgrade():
    # ====== Hapus tabel baru ======
    op.drop_table('user_roles')
    op.drop_table('roles')