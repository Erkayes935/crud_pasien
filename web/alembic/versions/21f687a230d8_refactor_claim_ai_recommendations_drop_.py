"""refactor claim_ai_recommendations: drop type, rename kategori, add stage

Revision ID: 21f687a230d8
Revises: 80d6970c8ee5
Create Date: 2025-09-17 11:34:51.131878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21f687a230d8'
down_revision: Union[str, None] = '80d6970c8ee5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. add kolom baru `nama_kategori`
    with op.batch_alter_table("claim_ai_recommendations") as batch_op:
        batch_op.add_column(sa.Column("nama_kategori", sa.String(length=50), nullable=True))

    # 2. drop kolom `type`
    with op.batch_alter_table("claim_ai_recommendations") as batch_op:
        batch_op.drop_column("type")

    # 3. add kolom `stage`
    with op.batch_alter_table("claim_ai_recommendations") as batch_op:
        batch_op.add_column(sa.Column("stage", sa.String(length=50), nullable=False, server_default="admission"))
        batch_op.alter_column("stage", server_default=None)


def downgrade():
    # rollback
    with op.batch_alter_table("claim_ai_recommendations") as batch_op:
        batch_op.add_column(sa.Column("type", sa.String(length=50), nullable=False, server_default="diagnosis"))
        batch_op.drop_column("stage")
        batch_op.drop_column("nama_kategori")