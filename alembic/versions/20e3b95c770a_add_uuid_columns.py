"""add uuid columns

Revision ID: 20e3b95c770a
Revises: 8fbc7184b1f2
Create Date: 2025-09-12 16:58:52.550081

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20e3b95c770a'
down_revision: Union[str, None] = '8fbc7184b1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # tabel-tabel utama yang butuh uuid
    tables = ["patients", "visits", "claims", "medical_records", "hospitals"]

    # tambahkan kolom uuid
    for table in tables:
        op.add_column(
            table,
            sa.Column(
                "uuid",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()"),
                unique=True,
            ),
        )

    # hapus server_default supaya ke depannya UUID digenerate dari sisi SQLAlchemy
    for table in tables:
        op.alter_column(table, "uuid", server_default=None)


def downgrade():
    tables = ["patients", "visits", "claims", "medical_records", "hospitals"]
    for table in tables:
        op.drop_column(table, "uuid")