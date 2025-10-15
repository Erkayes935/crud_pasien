"""add auth0_sub and multi-role support to users

Revision ID: 896385aebcf7
Revises: 354cc34b0acb
Create Date: 2025-10-14 10:04:04.415798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '896385aebcf7'
down_revision: Union[str, None] = '354cc34b0acb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def column_exists(conn, table_name, column_name):
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in cols


def table_exists(conn, table_name):
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)

    # --- USERS TABLE ---
    if table_exists(conn, "users"):
        with op.batch_alter_table("users") as batch_op:
            if not column_exists(conn, "users", "auth0_sub"):
                batch_op.add_column(sa.Column("auth0_sub", sa.String(), nullable=True))
                batch_op.create_index("ix_users_auth0_sub", ["auth0_sub"], unique=False)

            if not column_exists(conn, "users", "is_active"):
                batch_op.add_column(sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))

            if not column_exists(conn, "users", "is_deleted"):
                batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False))

            if not column_exists(conn, "users", "is_dummy"):
                batch_op.add_column(sa.Column("is_dummy", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    # --- ROLES TABLE ---
    if not table_exists(conn, "roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(50), unique=True, nullable=False),
            sa.Column("description", sa.String(255)),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        )

    # --- USER_ROLES TABLE ---
    if not table_exists(conn, "user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
            sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if table_exists(conn, "user_roles"):
        op.drop_table("user_roles")

    if table_exists(conn, "roles"):
        op.drop_table("roles")

    if table_exists(conn, "users"):
        with op.batch_alter_table("users") as batch_op:
            if column_exists(conn, "users", "auth0_sub"):
                batch_op.drop_index("ix_users_auth0_sub")
                batch_op.drop_column("auth0_sub")
            if column_exists(conn, "users", "is_active"):
                batch_op.drop_column("is_active")
            if column_exists(conn, "users", "is_deleted"):
                batch_op.drop_column("is_deleted")
            if column_exists(conn, "users", "is_dummy"):
                batch_op.drop_column("is_dummy")