"""Discover official country reports and preserve PDF pages for retrieval."""

import hashlib
import re
import time
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import HTTPException
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import Country, DebtReport, DebtReportChunk
from backend.app.models.entities import now
from backend.app.services.observations import require_country
from backend.app.services import live_world_bank

CATALOG_URL = "https://search.worldbank.org/api/v3/wds"
PDF_HOSTS = {
    "documents.worldbank.org",
    "documents1.worldbank.org",
    "thedocs.worldbank.org",
}
REPORT_TOPICS = (
    "debt",
    "economic update",
    "economic monitor",
    "public finance",
    "public expenditure",
    "macro poverty outlook",
)
MAX_PDF_BYTES = 32 * 1024 * 1024


def official_pdf_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.hostname not in PDF_HOSTS
        or parsed.scheme not in {"https", "http"}
        or parsed.port not in {None, 443}
    ):
        raise ValueError("The PDF must be hosted by the World Bank.")
    if parsed.username or parsed.password:
        raise ValueError("PDF URLs cannot include credentials.")
    if parsed.hostname == "documents.worldbank.org" and "/pdf/" in parsed.path:
        parsed = parsed._replace(netloc="documents1.worldbank.org")
    return parsed._replace(scheme="https", fragment="").geturl()


def fetch_json(client: httpx.Client, url: str, **params):
    for attempt in range(3):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            if attempt == 2:
                raise HTTPException(
                    502,
                    {
                        "code": "REPORT_SOURCE_UNAVAILABLE",
                        "message": "The World Bank report service could not be reached. Try again.",
                    },
                ) from None
            time.sleep(attempt + 1)


def discover_reports(db: Session, country_code: str) -> None:
    country = db.get(Country, country_code)
    if country is None:
        place = live_world_bank.country(country_code)
        country = Country(**place.model_dump())
        db.add(country)
        db.flush()
    with httpx.Client(
        timeout=40, headers={"User-Agent": "VEGA/0.1 (economic research)"}
    ) as client:
        metadata = fetch_json(
            client,
            f"https://api.worldbank.org/v2/country/{country.iso3}",
            format="json",
        )
        try:
            alpha2 = metadata[1][0]["iso2Code"]
        except (KeyError, IndexError, TypeError):
            raise HTTPException(
                502, "World Bank country metadata is unavailable."
            ) from None
        payload = fetch_json(
            client,
            CATALOG_URL,
            format="json",
            countrycode_exact=alpha2,
            qterm="debt",
            lang_exact="English",
            rows=100,
            srt="docdt",
            order="desc",
            enddate=date.today().isoformat(),
            fl="id,docdt,count,pdfurl,url,display_title,docty",
        )
    documents = payload.get("documents")
    if not isinstance(documents, dict):
        raise HTTPException(502, "World Bank report metadata is invalid.")
    found = 0
    for key, record in documents.items():
        if key == "facets" or not isinstance(record, dict):
            continue
        title = record.get("display_title", "")
        document_id = str(record.get("id", ""))
        if not any(topic in title.lower() for topic in REPORT_TOPICS):
            continue
        if any(
            word in title.lower()
            for word in ("procurement", "project", "disbursement", "lecture")
        ):
            continue
        try:
            pdf_url = official_pdf_url(record["pdfurl"])
            document_date = date.fromisoformat(record["docdt"][:10])
        except (KeyError, TypeError, ValueError):
            continue
        if not document_id.isdigit() or document_date > date.today():
            continue
        report = db.scalar(
            select(DebtReport).where(
                DebtReport.country_iso3 == country.iso3,
                DebtReport.document_id == document_id,
            )
        )
        if report is None:
            report = DebtReport(country_iso3=country.iso3, document_id=document_id)
            db.add(report)
        # Preserve the indexed PDF's metadata until an explicit reprocess succeeds.
        if report.indexed_at is None:
            report.title = title
            report.document_date = document_date
            report.pdf_url = pdf_url
            report.source_url = pdf_url.split("/pdf/")[0]
        report.discovered_at = now()
        found += 1
        if found == 10:
            break
    db.commit()


def _download_pdf_once(url: str) -> bytes:
    url = official_pdf_url(url)
    with httpx.Client(
        timeout=60, headers={"User-Agent": "VEGA/0.1 (economic research)"}
    ) as client:
        for _ in range(4):
            with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = official_pdf_url(urljoin(url, response.headers["location"]))
                    continue
                response.raise_for_status()
                content = bytearray()
                for block in response.iter_bytes():
                    content.extend(block)
                    if len(content) > MAX_PDF_BYTES:
                        raise ValueError("The PDF exceeds the 32 MB processing limit.")
                if not content.startswith(b"%PDF-"):
                    raise ValueError("The source did not return a PDF.")
                return bytes(content)
    raise ValueError("The PDF source redirected too many times.")


def download_pdf(url: str) -> bytes:
    for attempt in range(3):
        try:
            return _download_pdf_once(url)
        except httpx.HTTPError as error:
            if (
                isinstance(error, httpx.HTTPStatusError)
                and error.response.status_code < 500
                and error.response.status_code != 429
            ):
                raise
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def extract_chunks(content: bytes) -> tuple[int, list[dict]]:
    reader = PdfReader(BytesIO(content))
    if reader.is_encrypted or len(reader.pages) > 500:
        raise ValueError("Use an unencrypted report with at most 500 pages.")
    chunks = []
    for page_number, page in enumerate(reader.pages, 1):
        text = re.sub(
            r"\s+", " ", (page.extract_text() or "").replace("\x00", "")
        ).strip()
        if len(text) < 60 or text.count("....") > 5:
            continue
        start = 0
        chunk_index = 0
        while start < len(text):
            end = min(start + 1400, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start + 1000, end)
                if boundary > start:
                    end = boundary
            chunks.append(
                {
                    "page": page_number,
                    "chunk_index": chunk_index,
                    "text": text[start:end],
                }
            )
            if end == len(text):
                break
            overlap_start = text.find(" ", end - 200, end)
            start = overlap_start + 1 if overlap_start != -1 else end
            chunk_index += 1
    if not chunks:
        raise ValueError("This PDF has no readable text. It needs OCR before indexing.")
    return len(reader.pages), chunks


def process_report(
    db: Session, country_code: str, report_id: int, *, reprocess: bool = False
) -> DebtReport:
    report = db.scalar(
        select(DebtReport)
        .where(
            DebtReport.id == report_id,
            DebtReport.country_iso3 == country_code,
        )
        .with_for_update()
    )
    if report is None:
        raise HTTPException(404, "This report does not belong to the selected country.")
    try:
        content = download_pdf(report.pdf_url)
        digest = hashlib.sha256(content).hexdigest()
        if (
            report.content_hash == digest
            and report.status == "indexed"
            and not reprocess
        ):
            db.commit()
            return report
        page_count, chunks = extract_chunks(content)
        directory = get_settings().report_data_dir / country_code
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest}.pdf"
        # Content-addressed archives remain valid if a process fails before commit.
        if not path.exists():
            path.write_bytes(content)
        db.execute(
            delete(DebtReportChunk).where(DebtReportChunk.report_id == report.id)
        )
        db.add_all([DebtReportChunk(report_id=report.id, **chunk) for chunk in chunks])
        report.content_hash = digest
        report.page_count = page_count
        report.chunk_count = len(chunks)
        report.indexed_at = now()
        report.status = "indexed"
        report.error_message = None
        db.commit()
        return report
    except (httpx.HTTPError, ValueError, OSError, PdfReadError) as exc:
        db.rollback()
        report = db.get(DebtReport, report_id)
        if report.indexed_at is None:
            report.status = "failed"
        report.error_message = (
            str(exc)
            if isinstance(exc, ValueError)
            else "PDF download or storage failed. Try processing again."
        )
        db.commit()
        raise HTTPException(
            422, {"code": "PDF_PROCESSING_FAILED", "message": report.error_message}
        ) from None
