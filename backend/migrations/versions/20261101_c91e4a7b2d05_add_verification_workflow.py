"""add verification workflow

Revision ID: c91e4a7b2d05
Revises: b873ff0f1830
Create Date: 2026-11-01 21:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c91e4a7b2d05"
down_revision: str | Sequence[str] | None = "b873ff0f1830"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "verification_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("verifier_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "assigned",
                "in_review",
                "changes_requested",
                "signed_off",
                "approved",
                "rejected",
                name="assignmentstatus",
                native_enum=False,
                length=32,
            ),
            server_default="assigned",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["verifier_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index(
        op.f("ix_verification_assignments_verifier_id"),
        "verification_assignments",
        ["verifier_id"],
        unique=False,
    )
    op.create_table(
        "verification_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("verifier_id", sa.Integer(), nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "sign_off",
                "request_changes",
                name="reportdecision",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assignment_id"], ["verification_assignments.id"]),
        sa.ForeignKeyConstraint(["verifier_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verification_reports_assignment_id"),
        "verification_reports",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_reports_verifier_id"),
        "verification_reports",
        ["verifier_id"],
        unique=False,
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column(
            "decision",
            sa.Enum(
                "approved",
                "rejected",
                name="approvaldecision",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["verification_reports.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id"),
    )
    op.create_index(
        op.f("ix_approvals_approver_id"),
        "approvals",
        ["approver_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_approvals_approver_id"), table_name="approvals")
    op.drop_table("approvals")
    op.drop_index(op.f("ix_verification_reports_verifier_id"), table_name="verification_reports")
    op.drop_index(op.f("ix_verification_reports_assignment_id"), table_name="verification_reports")
    op.drop_table("verification_reports")
    op.drop_index(
        op.f("ix_verification_assignments_verifier_id"),
        table_name="verification_assignments",
    )
    op.drop_table("verification_assignments")
