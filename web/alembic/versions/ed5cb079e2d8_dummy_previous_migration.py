"""Dummy placeholder for missing migration ed5cb079e2d8.

This file is only created to keep Alembic migration history consistent.
It does not perform any schema changes.
"""

from alembic import op
import sqlalchemy as sa

# Keep these IDs consistent
revision = 'ed5cb079e2d8'
down_revision = None  # or the revision ID before this, if known
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
