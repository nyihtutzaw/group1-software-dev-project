"""add registry publications

Revision ID: b873ff0f1830
Revises: 0001
Create Date: 2026-10-28 03:45:48.595056
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b873ff0f1830"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "registry_credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("serial", sa.String(length=120), nullable=False),
        sa.Column("project_reference", sa.String(length=80), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("methodology", sa.String(length=200), nullable=False),
        sa.Column("vintage", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("verifier_name", sa.String(length=160), nullable=False),
        sa.Column("verification_reference", sa.String(length=80), nullable=False),
        sa.Column("approval_reference", sa.String(length=80), nullable=False),
        sa.Column("signed_off_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("developer_id", sa.Integer(), nullable=False),
        sa.Column("published_by_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'retired', 'revoked')", name="ck_registry_status"),
        sa.CheckConstraint("quantity > 0", name="ck_registry_quantity"),
        sa.CheckConstraint("vintage BETWEEN 1900 AND 2200", name="ck_registry_vintage"),
        sa.ForeignKeyConstraint(
            ["developer_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["published_by_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("serial"),
    )
    op.create_index(
        op.f("ix_registry_credits_project_reference"),
        "registry_credits",
        ["project_reference"],
        unique=False,
    )
    op.create_table(
        "registry_project_access",
        sa.Column("project_reference", sa.String(length=80), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["buyer_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("project_reference", "buyer_id"),
    )
    op.create_table(
        "registry_credit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credit_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('issued', 'retired', 'revoked')", name="ck_registry_event_action"
        ),
        sa.ForeignKeyConstraint(
            ["credit_id"],
            ["registry_credits.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_registry_credit_events_credit_id"),
        "registry_credit_events",
        ["credit_id"],
        unique=False,
    )
    op.create_table(
        "registry_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credit_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.String(length=200), nullable=False),
        sa.Column("buyer_visible", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["credit_id"],
            ["registry_credits.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_registry_evidence_credit_id"), "registry_evidence", ["credit_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_registry_evidence_credit_id"), table_name="registry_evidence")
    op.drop_table("registry_evidence")
    op.drop_index(op.f("ix_registry_credit_events_credit_id"), table_name="registry_credit_events")
    op.drop_table("registry_credit_events")
    op.drop_table("registry_project_access")
    op.drop_index(op.f("ix_registry_credits_project_reference"), table_name="registry_credits")
    op.drop_table("registry_credits")
