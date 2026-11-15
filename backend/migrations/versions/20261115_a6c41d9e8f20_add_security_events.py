"""add security events table

Revision ID: a6c41d9e8f20
Revises: f13d8a1b0c2e
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a6c41d9e8f20"
down_revision: str | Sequence[str] | None = "f13d8a1b0c2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "security_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("subject_hash", sa.String(length=64), nullable=True),
        sa.Column("source_ip", sa.String(length=45), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_events_actor_id"), "security_events", ["actor_id"], unique=False
    )
    op.create_index(
        op.f("ix_security_events_event_type"), "security_events", ["event_type"], unique=False
    )
    op.create_index(
        op.f("ix_security_events_source_ip"), "security_events", ["source_ip"], unique=False
    )
    op.create_index(
        op.f("ix_security_events_subject_hash"),
        "security_events",
        ["subject_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_security_events_created_at"), "security_events", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_security_events_created_at"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_subject_hash"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_source_ip"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_event_type"), table_name="security_events")
    op.drop_index(op.f("ix_security_events_actor_id"), table_name="security_events")
    op.drop_table("security_events")
