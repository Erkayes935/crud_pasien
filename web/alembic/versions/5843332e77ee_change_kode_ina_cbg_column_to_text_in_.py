"""Change kode_ina_cbg column to Text in claim_diagnosis_evaluations

Revision ID: 5843332e77ee
Revises: b7b8fa304555
Create Date: 2025-10-24 13:24:54.966511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5843332e77ee'
down_revision: Union[str, None] = 'b7b8fa304555'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column("claim_diagnosis_evaluations", "kode_ina_cbg",
                    existing_type=sa.String(length=50),
                    type_=sa.Text(),
                    existing_nullable=True)

def downgrade():
    # balikin lagi ke varchar(50) kalau rollback
    op.alter_column(
        "claim_diagnosis_evaluations",
        "kode_ina_cbg",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True
    )
