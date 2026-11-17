import asyncio
import json
from io import BytesIO
from zipfile import ZipFile

import httpx
import pytest
from sqlalchemy import func, select

from backend.app.models import Country, DataSnapshot, IngestionRun, Observation
from ingestion.connectors.world_bank import SourceError, WorldBankClient
from ingestion.indicators import WORLD_BANK_INDICATORS
from ingestion.pipelines.world_bank import ingest_world_bank
from ingestion.validation.records import ValidatedObservation, normalize_iso3
from backend.tests.conftest import ingest_fixture


def test_ingestion_preserves_null_zero_and_provenance(populated, tmp_path):
    assert populated.scalar(select(func.count()).select_from(Observation)) == 24
    assert populated.scalar(select(func.count()).select_from(Country)) == 2
    assert (
        populated.scalar(
            select(func.count())
            .select_from(Observation)
            .where(Observation.value.is_(None))
        )
        == 4
    )
    assert (
        populated.scalar(
            select(func.count()).select_from(Observation).where(Observation.value == 0)
        )
        == 10
    )
    row = populated.scalar(select(Observation))
    assert row.publication_date is None
    assert row.source_revision_date.isoformat() == "2025-01-01"
    assert row.retrieved_at is not None
    snapshot = populated.get(DataSnapshot, row.dataset_version)
    raw = json.loads(open(snapshot.raw_path).read())
    assert len(raw["pages"]) == 13
    assert raw["dataset_version"] == row.dataset_version
    assert "definition" in snapshot.manifest["indicators"][0]


def test_global_world_bank_import_preserves_coverage_and_missing_values(db, tmp_path):
    def fetch_archive(request):
        code = request.url.path.rsplit("/", 1)[-1]
        assert request.url.params["downloadformat"] == "csv"
        content = BytesIO()
        with ZipFile(content, "w") as archive:
            archive.writestr(
                "Metadata_Country_fixture.csv",
                "Country Code,Region,IncomeGroup,SpecialNotes,TableName\n"
                "USA,North America,High income,,United States\n"
                "WLD,,,,World\n",
            )
            archive.writestr(
                "Metadata_Indicator_fixture.csv",
                "INDICATOR_CODE,INDICATOR_NAME,SOURCE_NOTE\n"
                f"{code},Synthetic indicator,Synthetic definition\n",
            )
            archive.writestr(
                "API_fixture.csv",
                "Data Source,World Development Indicators\n\n"
                "Last Updated Date,2025-07-01\n\n"
                "Country Name,Country Code,Indicator Name,Indicator Code,2023,2024\n"
                f"United States,USA,Synthetic indicator,{code},0,\n"
                f"World,WLD,Synthetic indicator,{code},4,5\n",
            )
        return httpx.Response(200, content=content.getvalue())

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(fetch_archive)
        ) as client:
            return await ingest_world_bank(
                db, WorldBankClient(client), None, 2023, 2024, tmp_path
            )

    imported = asyncio.run(run())
    assert imported.records_processed == 2 * len(WORLD_BANK_INDICATORS)
    assert db.scalars(select(Country.iso3)).all() == ["USA"]
    observations = db.scalars(select(Observation)).all()
    assert all(
        row.source_revision_date.isoformat() == "2025-07-01" for row in observations
    )
    assert {row.value for row in observations} == {0.0, None}
    archive = json.loads((tmp_path / f"{imported.id}.json").read_text())
    assert len(archive["pages"]) == len(WORLD_BANK_INDICATORS)
    assert all("zip_base64" in page for page in archive["pages"])


def test_repeat_ingestion_is_idempotent(populated, tmp_path):
    first = populated.scalar(select(Observation)).dataset_version
    run = ingest_fixture(populated, tmp_path)
    assert run.dataset_version == first
    assert populated.scalar(select(func.count()).select_from(Observation)) == 24
    assert populated.scalar(select(func.count()).select_from(DataSnapshot)) == 1
    assert populated.scalar(select(func.count()).select_from(IngestionRun)) == 2


def test_changed_source_creates_immutable_vintage(populated, tmp_path):
    old_version = populated.scalar(select(Observation)).dataset_version
    ingest_fixture(populated, tmp_path, changed=True)
    assert populated.scalar(select(func.count()).select_from(DataSnapshot)) == 2
    assert populated.scalar(select(func.count()).select_from(Observation)) == 48
    assert (
        populated.scalar(
            select(func.count())
            .select_from(Observation)
            .where(Observation.dataset_version == old_version)
        )
        == 24
    )


@pytest.mark.parametrize("option", ["invalid", "missing", "fail"])
def test_failed_ingestion_is_atomic_and_audited(db, tmp_path, option):
    with pytest.raises((ValueError, SourceError)):
        ingest_fixture(db, tmp_path, **{option: True})
    assert db.scalar(select(func.count()).select_from(Observation)) == 0
    assert db.scalar(select(func.count()).select_from(Country)) == 0
    assert db.scalar(select(func.count()).select_from(DataSnapshot)) == 0
    run = db.scalar(select(IngestionRun))
    assert run.status == "failed" and run.finished_at is not None


@pytest.mark.parametrize("value", [True, "3.0", float("nan"), float("inf")])
def test_invalid_numeric_values_are_rejected(value):
    with pytest.raises(ValueError):
        ValidatedObservation(
            country_iso3="USA",
            indicator_code="test",
            observation_date="2024-01-01",
            value=value,
        )


def test_iso_normalization():
    assert normalize_iso3(" usa ") == "USA"
    with pytest.raises(ValueError):
        normalize_iso3("US")


def test_connector_paginates():
    def handler(request):
        page = int(request.url.params["page"])
        return httpx.Response(
            200, json=[{"page": page, "pages": 2, "total": 2}, [{"id": page}]]
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            connector = WorldBankClient(client)
            rows, metadata = await connector.fetch("country/all")
            assert rows == [{"id": 1}, {"id": 2}]
            assert len(metadata) == len(connector.raw_pages) == 2

    asyncio.run(run())


def test_connector_retries_rate_limit(monkeypatch):
    attempts = []

    async def no_wait(_):
        pass

    monkeypatch.setattr("ingestion.connectors.world_bank.asyncio.sleep", no_wait)

    def handler(request):
        attempts.append(request)
        if len(attempts) < 3:
            return httpx.Response(429)
        return httpx.Response(200, json=[{"page": 1, "pages": 1, "total": 0}, []])

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            rows, _ = await WorldBankClient(client).fetch("country/all")
            assert not rows

    asyncio.run(run())
    assert len(attempts) == 3


@pytest.mark.parametrize(
    "payload",
    [
        [{"message": [{"id": "120", "value": "Invalid value"}]}],
        [{"page": 2, "pages": 1}, []],
        [{"page": 1, "pages": 1, "total": 2}, None],
    ],
)
def test_connector_rejects_error_envelopes(payload):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
        ) as client:
            with pytest.raises(SourceError):
                await WorldBankClient(client).fetch("country/all")

    asyncio.run(run())
