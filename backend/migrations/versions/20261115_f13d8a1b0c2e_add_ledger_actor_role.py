"""add actor role snapshot to ledger entries

Revision ID: f13d8a1b0c2e
Revises: e24ad4024afd
Create Date: 2026-11-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f13d8a1b0c2e"
down_revision: str | Sequence[str] | None = "e24ad4024afd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ledger_entries", sa.Column("actor_role", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("ledger_entries", "actor_role")
