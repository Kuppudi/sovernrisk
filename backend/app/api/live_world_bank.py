import csv
import io
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import Field

from backend.app.schemas.api import (
    ISO3,
    CompareRequest,
    CompareResponse,
    CountryPage,
    IndicatorOut,
    MapDataOut,
    MapCountryOut,
    ModelStatus,
    ObservationOut,
    ObservationPage,
    ReportOut,
    YearFilter,
)
from backend.app.models.entities import now
from backend.app.services.reports import write_summary
from backend.app.services import live_world_bank as live
from backend.app.services.exports import protect_spreadsheet_text
from ingestion.indicators import WORLD_BANK_INDICATORS

router = APIRouter(prefix="/api/live/world-bank", tags=["World Bank live data"])


class LiveYearFilter(YearFilter):
    start_year: int = Field(default=2015, ge=2015, le=2025)
    end_year: int = Field(default=2025, ge=2015, le=2025)


class LiveCompareRequest(CompareRequest):
    start_year: int = Field(default=2015, ge=2015, le=2025)
    end_year: int = Field(default=2025, ge=2015, le=2025)


@router.get("/countries", response_model=CountryPage)
def countries(limit: int = Query(250, ge=1, le=250), offset: int = Query(0, ge=0)):
    places, _ = live.catalog(live.cache_bucket())
    return CountryPage(
        items=places[offset : offset + limit],
        total=len(places),
        limit=limit,
        offset=offset,
    )


@router.get("/indicators", response_model=list[IndicatorOut])
def indicators():
    return live.catalog(live.cache_bucket())[1]


@router.get("/map", response_model=MapDataOut)
def world_map(
    indicator: str = Query(min_length=1, max_length=100),
    year: int = Query(ge=2015, le=2025),
):
    bucket = live.cache_bucket()
    places, definitions = live.catalog(bucket)
    rows = live.observations(
        tuple(sorted(place.iso3 for place in places)), (indicator,), year, year, bucket
    )
    values = {row.country_iso3: row for row in rows}
    return MapDataOut(
        indicator=next(item for item in definitions if item.code == indicator),
        year=year,
        available_years=list(range(2025, 2014, -1)),
        source_name="World Bank WDI · API",
        source_url="https://data.worldbank.org/",
        countries=[
            MapCountryOut(
                **place.model_dump(),
                value=values[place.iso3].value if place.iso3 in values else None,
                observation_year=year if place.iso3 in values else None,
                retrieved_at=values[place.iso3].retrieved_at
                if place.iso3 in values
                else None,
                dataset_version=values[place.iso3].dataset_version
                if place.iso3 in values
                else None,
            )
            for place in places
        ],
    )


@router.get("/countries/{iso3}/indicators", response_model=ObservationPage)
def observations(
    iso3: ISO3,
    years: Annotated[LiveYearFilter, Query()],
    indicator: list[str] = Query(default=[], max_length=10),
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    rows = live.observations(
        (iso3,),
        tuple(sorted(set(indicator) or WORLD_BANK_INDICATORS)),
        years.start_year,
        years.end_year,
        live.cache_bucket(),
    )
    return ObservationPage(
        items=rows[offset : offset + limit], total=len(rows), limit=limit, offset=offset
    )


@router.get("/countries/{iso3}/indicators.csv")
def export_csv(
    iso3: ISO3,
    years: Annotated[LiveYearFilter, Query()],
    indicator: list[str] = Query(default=[], max_length=10),
):
    rows = live.observations(
        (iso3,),
        tuple(sorted(set(indicator) or WORLD_BANK_INDICATORS)),
        years.start_year,
        years.end_year,
        live.cache_bucket(),
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(ObservationOut.model_fields))
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: protect_spreadsheet_text(value)
                for key, value in row.model_dump(mode="json").items()
            }
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{iso3}-world-bank.csv"'
        },
    )


@router.post("/compare", response_model=CompareResponse)
def compare(body: LiveCompareRequest):
    places = [live.country(code) for code in body.countries]
    rows = live.observations(
        tuple(sorted(body.countries)),
        tuple(sorted(set(body.indicators) or WORLD_BANK_INDICATORS)),
        body.start_year,
        body.end_year,
        live.cache_bucket(),
    )
    return CompareResponse(countries=places, items=rows)


@router.get("/countries/{iso3}/report", response_model=ReportOut)
def country_report(iso3: ISO3):
    place = live.country(iso3)
    rows = live.observations(
        (iso3,), tuple(sorted(WORLD_BANK_INDICATORS)), 2015, 2025, live.cache_bucket()
    )
    latest = {}
    for row in rows:
        if row.value is not None:
            latest[row.indicator_code] = row
    return ReportOut(
        country=place,
        generated_at=now(),
        executive_summary=write_summary(place, list(latest.values())),
        latest_indicators=list(latest.values()),
        model_status=ModelStatus(),
        limitations=[
            "Annual World Bank observations are cached for up to five minutes. Missing values remain gaps.",
            "Latest non-missing years can differ between indicators. Forecasts and validated model scores are unavailable.",
        ],
    )
