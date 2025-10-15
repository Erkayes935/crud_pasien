"""add claim visit link

Revision ID: 952037d3c640
Revises: 0242f5008e2a
Create Date: 2025-10-11 10:50:03.109177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '952037d3c640'
down_revision: Union[str, None] = '0242f5008e2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        'claim_visit_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('claim_id', sa.Integer(), sa.ForeignKey('claims.id', ondelete='CASCADE'), nullable=False),
        sa.Column('external_visit_id', sa.String(100), nullable=False),
        sa.Column('hospital_id', sa.Integer(), sa.ForeignKey('hospitals.id'), nullable=True),
        sa.Column('is_primary', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('note', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )

def downgrade():
    op.drop_table('claim_visit_links')