from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import DebtReport
from backend.app.schemas.api import ISO3
from backend.app.schemas.debt_reports import (
    DebtReportList,
    DebtReportOut,
    ReportAnswer,
    ReportQuestion,
)
from backend.app.services.debt_reports import discover_reports, process_report
from backend.app.services.observations import require_country
from backend.app.services.report_rag import answer_question, generation_available

router = APIRouter(prefix="/api/countries/{iso3}/debt-reports", tags=["Debt reports"])
Db = Annotated[Session, Depends(get_db)]


@router.get("", response_model=DebtReportList)
def reports(iso3: ISO3, db: Db):
    items = db.scalars(
        select(DebtReport)
        .where(DebtReport.country_iso3 == iso3)
        .order_by(DebtReport.document_date.desc())
        .limit(50)
    ).all()
    return DebtReportList(items=items, generation_available=generation_available())


@router.post("/discover", response_model=DebtReportList)
def discover(iso3: ISO3, db: Db):
    discover_reports(db, iso3)
    return reports(iso3, db)


@router.post("/{report_id}/process", response_model=DebtReportOut)
def process(iso3: ISO3, report_id: int, db: Db, reprocess: bool = Query(False)):
    return process_report(db, iso3, report_id, reprocess=reprocess)


@router.post("/ask", response_model=ReportAnswer)
def ask(iso3: ISO3, body: ReportQuestion, db: Db):
    require_country(db, iso3)
    return answer_question(db, iso3, body)
