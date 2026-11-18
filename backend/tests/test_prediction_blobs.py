"""Synthetic result bundles only; no cloud calls or production model loading."""

import json
from datetime import UTC, datetime

import pytest
from azure.core.exceptions import ClientAuthenticationError
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.core.config import get_settings
from backend.app.schemas.prediction_bundle import PredictionBundle
from backend.app.services import prediction_blobs


@pytest.fixture
def bundle_data():
    return {
        "schema_version": 1, "status": "historical_research",
        "model_version": "synthetic-model", "dataset_version": "synthetic-snapshot",
        "generated_at": datetime.now(UTC).isoformat(), "target": "default_onset",
        "limitation": "Synthetic fixture; research only.",
        "countries": [
            {"iso3": code, "name": f"Synthetic {code}", "region": "Test", "income_group": "Test"}
            for code in ("AAA", "BBB")
        ],
        "predictions": [{
            "country_iso3": "AAA", "as_of_date": "2024-12-31", "risk_score": 0.125,
            "downgrade_probability_12m": None, "model_version": "synthetic-model",
            "generated_at": datetime.now(UTC).isoformat(), "data_snapshot_id": "synthetic-snapshot",
            "research_only": True, "outcome_year": 2025, "feature_year": 2023,
        }],
    }


def test_blob_mode_serves_status_map_and_country_without_sql(client, db, bundle_data, monkeypatch):
    monkeypatch.setattr(get_settings(), "predictions_blob_url", "https://example.blob.core.windows.net/results/current.json")
    bundle = PredictionBundle.model_validate(bundle_data)
    monkeypatch.setattr("backend.app.services.predictions.load_bundle", lambda url: bundle)
    # All countries and score metadata must come from the bundle, not SQL catalogs.
    monkeypatch.setattr(db, "scalar", lambda *a, **k: pytest.fail("Unexpected SQL query"))
    monkeypatch.setattr(db, "scalars", lambda *a, **k: pytest.fail("Unexpected SQL query"))
    status = client.get("/api/models/status").json()
    assert status["status"] == "available" and status["research_only"] is True
    assert status["outcome_year"] == 2025
    result = client.get("/api/countries/AAA/prediction").json()
    assert result["risk_score"] == 0.125 and result["outcome_year"] == 2025
    assert client.get("/api/countries/BBB/prediction").status_code == 404
    assert client.get("/api/countries/CCC/prediction").status_code == 404
    mapped = client.get("/api/data/map?indicator=default-risk&year=2026").json()
    assert mapped["year"] == 2025 and mapped["research_only"] is True
    assert [country["value"] for country in mapped["countries"]] == [0.125, None]


@pytest.mark.parametrize("change", ["probability", "duplicate", "country", "provenance", "year"])
def test_bundle_rejects_invalid_results(bundle_data, change):
    row = bundle_data["predictions"][0]
    if change == "probability":
        row["risk_score"] = float("nan")
    elif change == "duplicate":
        bundle_data["predictions"].append(row.copy())
    elif change == "country":
        row["country_iso3"] = "CCC"
    elif change == "provenance":
        row["data_snapshot_id"] = "wrong-snapshot"
    else:
        row["outcome_year"] = 2026
    with pytest.raises(ValidationError):
        PredictionBundle.model_validate(bundle_data)


def test_blob_cache_refresh_and_failed_auth(bundle_data, monkeypatch):
    prediction_blobs._read_bundle.cache_clear()
    calls = []
    class SyntheticClient:
        def download_blob(self, **options):
            calls.append(options)
            return self

        def readall(self):
            return json.dumps(bundle_data).encode()

    monkeypatch.setattr(prediction_blobs, "blob_client", lambda url: SyntheticClient())
    url = "https://example.blob.core.windows.net/results/current.json"
    first = prediction_blobs._read_bundle(url, 1)
    assert prediction_blobs._read_bundle(url, 1) is first
    assert len(calls) == 1
    prediction_blobs._read_bundle(url, 2)
    assert len(calls) == 2
    prediction_blobs._read_bundle.cache_clear()
    def unavailable(url):
        raise ClientAuthenticationError("Synthetic access failure")
    monkeypatch.setattr(prediction_blobs, "blob_client", unavailable)
    with pytest.raises(HTTPException) as error:
        prediction_blobs.load_bundle(url)
    assert error.value.status_code == 503


@pytest.mark.parametrize("url", ["http://example.com/a/b", "https://example.com/a/b", "https://x.blob.core.windows.net/a/b?sig=secret"])
def test_blob_settings_reject_keys_and_non_azure_hosts(url):
    with pytest.raises(ValueError):
        prediction_blobs.validate_blob_url(url)
