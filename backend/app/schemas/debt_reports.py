from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.api import ModelStatus, ObservationOut


class DebtReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    country_iso3: str
    document_id: str
    title: str
    document_date: date
    pdf_url: str
    source_url: str
    discovered_at: datetime
    indexed_at: datetime | None
    page_count: int
    chunk_count: int
    status: str
    error_message: str | None


class DebtReportList(BaseModel):
    items: list[DebtReportOut]
    generation_available: bool
    provider: str = "Azure OpenAI"
    coverage_note: str = "Latest matching English-language debt and economic reports in the World Bank catalog. Availability differs by country."


class ReportQuestion(BaseModel):
    question: str = Field(min_length=5, max_length=1500)
    generate: bool = False
    report_ids: list[int] = Field(default_factory=list, max_length=10)


class ReportCitation(BaseModel):
    id: str
    report_id: int
    title: str
    document_date: date
    page: int
    text: str
    url: str


class ReportAnswer(BaseModel):
    answer: str | None
    mode: Literal["passages", "generated", "no_matches"]
    citations: list[ReportCitation]
    model_status: ModelStatus
    indicators: list[ObservationOut]
    generation_available: bool
