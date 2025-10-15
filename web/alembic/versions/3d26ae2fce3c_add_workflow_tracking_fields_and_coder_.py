"""add workflow tracking fields and coder verification

Revision ID: 3d26ae2fce3c
Revises: d44eb46558c1
Create Date: 2025-10-12 11:25:29.617998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '3d26ae2fce3c'
down_revision: Union[str, None] = 'd44eb46558c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def column_not_exists(conn, table_name, column_name):
    insp = inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name not in cols


def upgrade():
    conn = op.get_bind()

    # === CLAIMS TABLE ===
    new_claim_columns = [
        ("workflow_status", sa.Column("workflow_status", sa.String(), server_default="draft")),
        ("doctor_submitted_by", sa.Column("doctor_submitted_by", sa.String())),
        ("doctor_submitted_at", sa.Column("doctor_submitted_at", sa.DateTime())),
        ("coder_verified_by", sa.Column("coder_verified_by", sa.String())),
        ("coder_verified_at", sa.Column("coder_verified_at", sa.DateTime())),
        ("finalized_by", sa.Column("finalized_by", sa.String())),
        ("finalized_at", sa.Column("finalized_at", sa.DateTime())),
        ("ai_medical_resume", sa.Column("ai_medical_resume", sa.Text())),
    ]
    for col_name, col_def in new_claim_columns:
        if column_not_exists(conn, "claims", col_name):
            op.add_column("claims", col_def)

    # === CLAIM_SIMULATIONS TABLE ===
    new_sim_columns = [
        ("coder_verified", sa.Column("coder_verified", sa.Boolean(), server_default="false")),
        ("coder_verified_by", sa.Column("coder_verified_by", sa.String())),
        ("coder_verified_at", sa.Column("coder_verified_at", sa.DateTime())),
        ("coder_notes", sa.Column("coder_notes", sa.Text())),
        ("verified_icd10", sa.Column("verified_icd10", sa.String())),
        ("verified_icd10_name", sa.Column("verified_icd10_name", sa.Text())),
        ("verified_icd9", sa.Column("verified_icd9", sa.String())),
        ("verified_icd9_name", sa.Column("verified_icd9_name", sa.Text())),
        ("is_coder_approved", sa.Column("is_coder_approved", sa.Boolean(), server_default="false")),
    ]
    for col_name, col_def in new_sim_columns:
        if column_not_exists(conn, "claim_simulations", col_name):
            op.add_column("claim_simulations", col_def)


def downgrade():
    conn = op.get_bind()

    safe_drop = [
        ("claims", [
            "workflow_status", "doctor_submitted_by", "doctor_submitted_at",
            "coder_verified_by", "coder_verified_at", "finalized_by",
            "finalized_at", "ai_medical_resume"
        ]),
        ("claim_simulations", [
            "coder_verified", "coder_verified_by", "coder_verified_at",
            "coder_notes", "verified_icd10", "verified_icd10_name",
            "verified_icd9", "verified_icd9_name", "is_coder_approved"
        ]),
    ]

    for table, cols in safe_drop:
        for col in cols:
            try:
                op.drop_column(table, col)
            except Exception:
                pass