"""Synthetic documents only. These fixtures never enter application data."""

from datetime import date
from io import BytesIO

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import func, select

from backend.app.core.config import get_settings
from backend.app.models import DebtReport, DebtReportChunk
from backend.app.schemas.debt_reports import ReportQuestion
from backend.app.services.debt_reports import (
    extract_chunks,
    official_pdf_url,
    process_report,
)
from backend.app.services.report_rag import generate_answer, retrieve_passages


def synthetic_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    content = DecodedStreamObject()
    content.set_data(
        b"BT /F1 12 Tf 30 700 Td (Synthetic debt report. Refinancing pressure increases when debt service costs rise and foreign reserves decline.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def add_report(db, country, document_id):
    report = DebtReport(
        country_iso3=country,
        document_id=document_id,
        title="Synthetic debt report",
        document_date=date(2026, 1, 1),
        pdf_url="https://documents1.worldbank.org/synthetic.pdf",
        source_url="https://documents.worldbank.org/synthetic",
    )
    db.add(report)
    db.commit()
    return report


def test_pdf_processing_is_idempotent_and_preserves_page_citations(
    populated, monkeypatch, tmp_path
):
    report = add_report(populated, "USA", "synthetic-1")
    monkeypatch.setenv("REPORT_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(
        "backend.app.services.debt_reports.download_pdf", lambda _: synthetic_pdf()
    )
    try:
        process_report(populated, "USA", report.id)
        process_report(populated, "USA", report.id)
        assert populated.scalar(select(func.count()).select_from(DebtReportChunk)) == 1
        citations = retrieve_passages(
            populated,
            "USA",
            ReportQuestion(question="What drives refinancing pressure?"),
        )
        assert citations[0].page == 1
        assert citations[0].url.endswith("#page=1")
        assert "Refinancing pressure" in citations[0].text
        assert not retrieve_passages(
            populated,
            "IND",
            ReportQuestion(question="What drives refinancing pressure?"),
        )
        assert list(tmp_path.rglob("*.pdf"))
    finally:
        get_settings.cache_clear()


def test_processing_failure_keeps_previous_index(populated, monkeypatch, tmp_path):
    report = add_report(populated, "USA", "synthetic-2")
    monkeypatch.setenv("REPORT_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(
        "backend.app.services.debt_reports.download_pdf", lambda _: synthetic_pdf()
    )
    try:
        process_report(populated, "USA", report.id)

        def fail(_):
            raise ValueError("Synthetic download failure")

        monkeypatch.setattr("backend.app.services.debt_reports.download_pdf", fail)
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            process_report(populated, "USA", report.id)
        assert populated.get(DebtReport, report.id).status == "indexed"
        assert populated.scalar(select(func.count()).select_from(DebtReportChunk)) == 1
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/report.pdf",
        "http://127.0.0.1/report.pdf",
        "https://documents.worldbank.org@evil.example/a.pdf",
    ],
)
def test_pdf_sources_are_restricted_to_official_hosts(url):
    with pytest.raises(ValueError):
        official_pdf_url(url)


def test_azure_answer_requires_existing_page_citations(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://synthetic.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "synthetic-chat")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "synthetic-key")
    get_settings.cache_clear()
    calls = []

    def post(self, url, **kwargs):
        calls.append(kwargs)
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"answer":"Synthetic debt pressure rose [R1]."}'
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx.Client, "post", post)
    try:
        answer = generate_answer("Explain debt risk", {"passages": [{"id": "R1"}]})
        assert "[R1]" in answer
        assert calls[0]["headers"]["api-key"] == "synthetic-key"
        assert calls[0]["json"]["model"] == "synthetic-chat"
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            generate_answer("Explain debt risk", {"passages": [{"id": "R2"}]})
    finally:
        get_settings.cache_clear()


def test_report_api_handles_missing_reports_and_never_fabricates_scores(
    client, populated
):
    listing = client.get("/api/countries/USA/debt-reports")
    assert listing.status_code == 200
    assert listing.json()["items"] == []
    answer = client.post(
        "/api/countries/USA/debt-reports/ask",
        json={"question": "What are the debt risks?"},
    )
    assert answer.status_code == 200
    assert answer.json()["mode"] == "no_matches"
    assert answer.json()["model_status"]["status"] == "unavailable"
