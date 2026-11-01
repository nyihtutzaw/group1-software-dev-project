"""add registration fields and evidence files (F1)

Revision ID: 47c89f71feec
Revises: b873ff0f1830
Create Date: 2026-11-02 16:41:28.811936
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "47c89f71feec"
down_revision: str | Sequence[str] | None = "b873ff0f1830"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Evidence is WORM: once a row exists it can never be changed or removed, whatever code path
# (or psql session) tries. Rolling back the inserting transaction is still possible.
WRITE_ONCE_FUNCTION = """
CREATE FUNCTION evidence_files_write_once() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'evidence_files is write-once: % is not allowed', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql
"""


def upgrade() -> None:
    op.add_column("projects", sa.Column("methodology", sa.String(length=20), nullable=True))
    op.add_column("projects", sa.Column("crediting_start_year", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("crediting_end_year", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("area_ha", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("est_removal_tco2e", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("baseline_summary", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("additionality_reasoning", sa.Text(), nullable=True))
    op.add_column(
        "projects",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column("projects", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    # Numbers for new project codes (CRVR-0200, …); below 200 is taken by the demo projects.
    op.execute("CREATE SEQUENCE project_code_seq START 200")

    op.create_table(
        "evidence_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "land_title",
                "survey",
                "photo",
                "gps",
                "spreadsheet",
                "additionality_proof",
                "other",
                name="evidencekind",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=200), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "sealed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_evidence_files_project_id"), "evidence_files", ["project_id"], unique=False
    )
    op.execute(WRITE_ONCE_FUNCTION)
    op.execute(
        "CREATE TRIGGER evidence_files_write_once BEFORE UPDATE OR DELETE ON evidence_files "
        "FOR EACH ROW EXECUTE FUNCTION evidence_files_write_once()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER evidence_files_write_once ON evidence_files")
    op.execute("DROP FUNCTION evidence_files_write_once()")
    op.drop_index(op.f("ix_evidence_files_project_id"), table_name="evidence_files")
    op.drop_table("evidence_files")
    op.execute("DROP SEQUENCE project_code_seq")
    op.drop_column("projects", "submitted_at")
    op.drop_column("projects", "updated_at")
    op.drop_column("projects", "additionality_reasoning")
    op.drop_column("projects", "baseline_summary")
    op.drop_column("projects", "est_removal_tco2e")
    op.drop_column("projects", "area_ha")
    op.drop_column("projects", "crediting_end_year")
    op.drop_column("projects", "crediting_start_year")
    op.drop_column("projects", "methodology")
