"""Change String columns to Text in evaluation tables

Revision ID: 387475cdff47
Revises: ed5cb079e2d8
Create Date: 2025-10-24 11:21:26.237931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '387475cdff47'
down_revision: Union[str, None] = 'ed5cb079e2d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ClaimDiagnosisEvaluation
    op.alter_column("claim_diagnosis_evaluations", "validitas_detail", type_=sa.Text())
    op.alter_column("claim_diagnosis_evaluations", "severity", type_=sa.Text())

    # ClaimProcedureEvaluation
    op.alter_column("claim_procedure_evaluations", "validitas_detail", type_=sa.Text())

    # ClaimCombinationAlternative
    op.alter_column("claim_combination_alternatives", "severity", type_=sa.Text())

    # ClaimIDRGSummary
    op.alter_column("claim_idrg_summary", "severity_kombinasi", type_=sa.Text())
    op.alter_column("claim_idrg_summary", "gap_inacbg_vs_idrg", type_=sa.Text())

def downgrade():
    op.alter_column("claim_diagnosis_evaluations", "validitas_detail", type_=sa.String(length=255))
    op.alter_column("claim_diagnosis_evaluations", "severity", type_=sa.String(length=50))
    op.alter_column("claim_procedure_evaluations", "validitas_detail", type_=sa.String(length=255))
    op.alter_column("claim_combination_alternatives", "severity", type_=sa.String(length=50))
    op.alter_column("claim_idrg_summary", "severity_kombinasi", type_=sa.String(length=50))
    op.alter_column("claim_idrg_summary", "gap_inacbg_vs_idrg", type_=sa.String(length=50))
