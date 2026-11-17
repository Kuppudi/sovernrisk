from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base
from backend.app.models.entities import now


class DebtReport(Base):
    __tablename__ = "debt_reports"
    __table_args__ = (
        UniqueConstraint(
            "country_iso3", "document_id", name="uq_debt_report_country_document"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_iso3: Mapped[str] = mapped_column(ForeignKey("countries.iso3"), index=True)
    document_id: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(Text)
    document_date: Mapped[date]
    pdf_url: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    page_count: Mapped[int] = mapped_column(default=0)
    chunk_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(30), default="discovered")
    error_message: Mapped[str | None] = mapped_column(Text)


class DebtReportChunk(Base):
    __tablename__ = "debt_report_chunks"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "page", "chunk_index", name="uq_debt_report_chunk"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("debt_reports.id", ondelete="CASCADE"), index=True
    )
    page: Mapped[int]
    chunk_index: Mapped[int]
    text: Mapped[str] = mapped_column(Text)
