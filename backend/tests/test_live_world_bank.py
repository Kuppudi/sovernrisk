"""Exercise the live proxy with isolated, explicitly synthetic World Bank data."""

from datetime import date, datetime, UTC

from backend.app.schemas.api import CountryOut, IndicatorOut, ObservationOut
from ingestion.indicators import WORLD_BANK_INDICATORS


def test_live_frontend_reads_work_without_imported_observations(client, monkeypatch):
    from backend.app.services import live_world_bank as live

    country = CountryOut(
        iso3="USA", name="Synthetic USA", region="Test", income_group="Test"
    )
    definitions = [
        IndicatorOut(
            code=code,
            name="Synthetic indicator",
            definition="Synthetic definition",
            source_id=0,
            **meta,
        )
        for code, meta in WORLD_BANK_INDICATORS.items()
    ]
    monkeypatch.setattr(live, "catalog", lambda bucket: ([country], definitions))

    def observations(countries, codes, start, end, bucket):
        return [
            ObservationOut(
                country_iso3="USA",
                indicator_code=code,
                indicator_name="Synthetic indicator",
                unit=WORLD_BANK_INDICATORS[code]["unit"],
                observation_date=date(year, 1, 1),
                value=None if year == 2025 else 0.0,
                publication_date=None,
                source_revision_date=date(2026, 1, 1),
                retrieved_at=datetime.now(UTC),
                dataset_version="a" * 64,
                source="Synthetic World Bank",
                source_url="https://example.invalid",
            )
            for code in codes
            for year in range(start, end + 1)
        ]

    monkeypatch.setattr(live, "observations", observations)
    assert client.get("/api/live/world-bank/countries").json()["total"] == 1
    page = client.get(
        "/api/live/world-bank/countries/USA/indicators?start_year=2015&end_year=2025&limit=50&offset=50"
    ).json()
    assert page["total"] == 110
    assert len(page["items"]) == 50
    response = client.get("/api/live/world-bank/map?indicator=NY.GDP.MKTP.CD&year=2025")
    assert response.status_code == 200
    assert response.json()["countries"][0]["value"] is None
    csv = client.get(
        "/api/live/world-bank/countries/USA/indicators.csv?indicator=NY.GDP.MKTP.CD&start_year=2024&end_year=2025"
    )
    assert "0.0" in csv.text and "2025-01-01,," in csv.text
