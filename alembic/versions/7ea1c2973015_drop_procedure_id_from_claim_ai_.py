"""drop procedure_id from claim_ai_recommendations

Revision ID: 7ea1c2973015
Revises: 5775ea6affdc
Create Date: 2025-09-26 13:50:59.597153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ea1c2973015'
down_revision: Union[str, None] = '5775ea6affdc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_constraint('claim_ai_recommendations_procedure_id_fkey', 'claim_ai_recommendations', type_='foreignkey')
    op.drop_column('claim_ai_recommendations', 'procedure_id')

def downgrade():
    op.add_column('claim_ai_recommendations', sa.Column('procedure_id', sa.Integer(), nullable=True))
    op.create_foreign_key('claim_ai_recommendations_procedure_id_fkey', 'claim_ai_recommendations', 'claim_procedures', ['procedure_id'], ['id'])

