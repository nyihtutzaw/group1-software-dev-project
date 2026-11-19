"""buffer pool and verifier reassignment

Revision ID: b7c2e4a91d08
Revises: a8dd7b5de443
Create Date: 2026-11-19 12:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2e4a91d08"
down_revision: str | Sequence[str] | None = "a8dd7b5de443"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "verification_reports", sa.Column("risk_rating", sa.String(length=8), nullable=True)
    )
    op.create_check_constraint(
        "ck_verification_report_risk",
        "verification_reports",
        "risk_rating IS NULL OR risk_rating IN ('low', 'medium', 'high')",
    )
    op.create_table(
        "verification_reassignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("previous_verifier_id", sa.Integer(), nullable=False),
        sa.Column("verifier_id", sa.Integer(), nullable=False),
        sa.Column("previous_due_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["verification_assignments.id"]),
        sa.ForeignKeyConstraint(["previous_verifier_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["verifier_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verification_reassignments_assignment_id"),
        "verification_reassignments",
        ["assignment_id"],
        unique=False,
    )
    op.drop_constraint("ck_registry_status", "registry_credits", type_="check")
    op.create_check_constraint(
        "ck_registry_status",
        "registry_credits",
        "status IN ('active', 'retired', 'revoked', 'buffer')",
    )
    op.drop_constraint(
        "registry_credits_source_approval_id_key", "registry_credits", type_="unique"
    )
    op.create_unique_constraint(
        "uq_registry_credits_approval_status",
        "registry_credits",
        ["source_approval_id", "status"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_registry_credits_approval_status", "registry_credits", type_="unique")
    op.create_unique_constraint(
        "registry_credits_source_approval_id_key", "registry_credits", ["source_approval_id"]
    )
    op.drop_constraint("ck_registry_status", "registry_credits", type_="check")
    op.create_check_constraint(
        "ck_registry_status",
        "registry_credits",
        "status IN ('active', 'retired', 'revoked')",
    )
    op.drop_index(
        op.f("ix_verification_reassignments_assignment_id"),
        table_name="verification_reassignments",
    )
    op.drop_table("verification_reassignments")
    op.drop_constraint("ck_verification_report_risk", "verification_reports", type_="check")
    op.drop_column("verification_reports", "risk_rating")
