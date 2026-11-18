"""Synthetic result bundles only; no cloud calls or production model loading."""

import json
from copy import deepcopy

import pytest
from azure.core.exceptions import ClientAuthenticationError
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.core.config import get_settings
from backend.app.schemas.prediction_bundle import PredictionBundle
from backend.app.services import prediction_blobs
from ingestion.indicators import GLOBAL_INDICATORS


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


def test_packaged_results_take_priority_without_cloud_access(client, db, bundle_data, monkeypatch, tmp_path):
    path = tmp_path / "frontend_predictions.json"
    path.write_text(json.dumps(bundle_data))
    monkeypatch.setattr("backend.app.services.predictions.PACKAGED_PREDICTIONS", path)
    monkeypatch.setattr(get_settings(), "predictions_file", "")
    monkeypatch.setattr(get_settings(), "predictions_blob_url", "https://blocked.blob.core.windows.net/a/b.json")
    monkeypatch.setattr("backend.app.services.predictions.load_bundle", lambda *a: pytest.fail("Blob access attempted"))
    monkeypatch.setattr(db, "scalar", lambda *a, **k: pytest.fail("SQL access attempted"))
    monkeypatch.setattr(db, "scalars", lambda *a, **k: pytest.fail("SQL access attempted"))
    assert client.get("/api/models/status").json()["status"] == "available"
    assert client.get("/api/countries/AAA/prediction").json()["risk_score"] == 0.125
    mapped = client.get("/api/data/map?indicator=default-risk&year=2025").json()
    assert [row["value"] for row in mapped["countries"]] == [0.125, None]
    # An invalid replacement must not silently use old cached results or Blob.
    path.write_text('{"invalid":true}')
    response = client.get("/api/models/status")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PREDICTIONS_UNAVAILABLE"


def test_explicit_missing_result_file_fails_without_blob_fallback(client, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "predictions_file", str(tmp_path / "missing.json"))
    monkeypatch.setattr("backend.app.services.predictions.load_bundle", lambda *a: pytest.fail("Blob access attempted"))
    assert client.get("/api/models/status").status_code == 503


def test_latest_bundle_counts_only_supported_scores_and_serves_coverage(client, db, bundle_data, monkeypatch):
    features = list(GLOBAL_INDICATORS)
    bundle_data.update(schema_version=2, status="latest_research", feature_codes=features, max_feature_age_years=2)
    row = bundle_data["predictions"][0]
    row.update(research_kind="latest_research", as_of_date="2026-11-18", outcome_year=2027,
               feature_year=2025, observed_feature_count=4, in_training_coverage=False,
               feature_years={feature: 2025 for feature in features[:4]})
    missing = deepcopy(row)
    missing.update(country_iso3="BBB", risk_score=None, availability="insufficient_data",
                   observed_feature_count=3, feature_years={feature: 2024 for feature in features[:3]})
    bundle_data["predictions"].append(missing)
    bundle = PredictionBundle.model_validate(bundle_data)
    monkeypatch.setattr(get_settings(), "predictions_blob_url", "https://example.blob.core.windows.net/results/current.json")
    monkeypatch.setattr("backend.app.services.predictions.load_bundle", lambda url: bundle)
    monkeypatch.setattr(db, "scalar", lambda *a, **k: pytest.fail("Unexpected SQL query"))
    status = client.get("/api/models/status").json()
    assert status["predictions_available"] == 1 and status["outcome_year"] == 2027
    assert status["research_kind"] == "latest_research"
    result = client.get("/api/countries/BBB/prediction").json()
    assert result["risk_score"] is None and result["availability"] == "insufficient_data"
    mapped = client.get("/api/data/map?indicator=default-risk&year=2025").json()
    assert mapped["year"] == 2027 and mapped["research_kind"] == "latest_research"
    assert [row["value"] for row in mapped["countries"]] == [0.125, None]
    missing["risk_score"] = 0.5
    with pytest.raises(ValidationError, match="availability"):
        PredictionBundle.model_validate(bundle_data)


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
