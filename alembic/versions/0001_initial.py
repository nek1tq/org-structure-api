"""initial schema: departments and employees

Revision ID: 0001
Revises:
Create Date: 2026-05-14 00:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 200", name="ck_departments_name_length"
        ),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_departments_no_self_parent",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["departments.id"],
            name="fk_departments_parent_id_departments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint(
            "parent_id", "name", name="uq_departments_parent_id_name"
        ),
    )
    op.create_index(
        "ix_departments_parent_id", "departments", ["parent_id"], unique=False
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("position", sa.String(length=200), nullable=False),
        sa.Column("hired_at", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(full_name) BETWEEN 1 AND 200",
            name="ck_employees_full_name_length",
        ),
        sa.CheckConstraint(
            "char_length(position) BETWEEN 1 AND 200",
            name="ck_employees_position_length",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_employees_department_id_departments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_employees"),
    )
    op.create_index(
        "ix_employees_department_id", "employees", ["department_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_employees_department_id", table_name="employees")
    op.drop_table("employees")
    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_table("departments")
