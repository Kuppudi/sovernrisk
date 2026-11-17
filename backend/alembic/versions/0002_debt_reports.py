"""Country report metadata and page-preserving retrieval chunks."""

from alembic import op
import sqlalchemy as sa

revision = "0002_debt_reports"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "debt_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "country_iso3",
            sa.String(3),
            sa.ForeignKey("countries.iso3"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(80), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=False),
        sa.Column("pdf_url", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.UniqueConstraint(
            "country_iso3", "document_id", name="uq_debt_report_country_document"
        ),
    )
    op.create_index("ix_debt_reports_country_iso3", "debt_reports", ["country_iso3"])
    op.create_table(
        "debt_report_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "report_id",
            sa.Integer(),
            sa.ForeignKey("debt_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "report_id", "page", "chunk_index", name="uq_debt_report_chunk"
        ),
    )
    op.create_index(
        "ix_debt_report_chunks_report_id", "debt_report_chunks", ["report_id"]
    )


def downgrade():
    op.drop_table("debt_report_chunks")
    op.drop_table("debt_reports")
