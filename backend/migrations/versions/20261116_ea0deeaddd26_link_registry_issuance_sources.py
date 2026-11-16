"""link registry credits to issuance sources

Revision ID: ea0deeaddd26
Revises: a6c41d9e8f20
Create Date: 2026-11-16 09:07:41.625546
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ea0deeaddd26"
down_revision: str | Sequence[str] | None = "a6c41d9e8f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("registry_credits", sa.Column("source_project_id", sa.Integer(), nullable=True))
    op.add_column("registry_credits", sa.Column("source_approval_id", sa.Integer(), nullable=True))
    op.add_column(
        "registry_credits",
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index(
        op.f("ix_registry_credits_source_project_id"),
        "registry_credits",
        ["source_project_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "registry_credits_source_approval_id_key", "registry_credits", ["source_approval_id"]
    )
    op.create_foreign_key(
        "registry_credits_source_approval_id_fkey",
        "registry_credits",
        "approvals",
        ["source_approval_id"],
        ["id"],
    )
    op.create_foreign_key(
        "registry_credits_source_project_id_fkey",
        "registry_credits",
        "projects",
        ["source_project_id"],
        ["id"],
    )

    for index in range(1, 4):
        op.execute(
            sa.text(
                "UPDATE registry_credits SET is_demo = true "
                "WHERE serial = :serial AND project_reference = :reference"
            ).bindparams(
                serial=f"DEMO-{index:04d}-2026-A-00001-00100", reference=f"DEMO-{index:04d}"
            )
        )


def downgrade() -> None:
    op.drop_constraint(
        "registry_credits_source_project_id_fkey", "registry_credits", type_="foreignkey"
    )
    op.drop_constraint(
        "registry_credits_source_approval_id_fkey", "registry_credits", type_="foreignkey"
    )
    op.drop_constraint(
        "registry_credits_source_approval_id_key", "registry_credits", type_="unique"
    )
    op.drop_index(op.f("ix_registry_credits_source_project_id"), table_name="registry_credits")
    op.drop_column("registry_credits", "is_demo")
    op.drop_column("registry_credits", "source_approval_id")
    op.drop_column("registry_credits", "source_project_id")
