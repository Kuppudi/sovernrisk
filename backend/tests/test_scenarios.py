"""The ordinary API must work without models or optional ML dependencies."""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app


def test_scenario_catalog_and_unconfigured_status_need_no_ml_or_sql(monkeypatch):
    monkeypatch.setattr(get_settings(), "scenario_model_file", "")
    with TestClient(app) as client:
        catalog = client.get("/api/scenarios/presets")
        assert catalog.status_code == 200
        assert len(catalog.json()) == 3
        response = client.post("/api/scenarios", json={"country_iso3": "IND", "presets": ["growth_slowdown"]})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SCENARIO_NOT_CONFIGURED"


@pytest.mark.parametrize("body", [
    {"country_iso3": "IND", "presets": []},
    {"country_iso3": "IND", "presets": ["growth_slowdown", "growth_slowdown"]},
    {"country_iso3": "IND", "presets": ["commodity_shock"]},
    {"country_iso3": "IND", "presets": ["growth_slowdown"], "model_path": "/tmp/untrusted.joblib"},
    {"country_iso3": "IND", "presets": ["growth_slowdown"], "feature_year": 2010},
    {"country_iso3": "???", "presets": ["growth_slowdown"]},
])
def test_scenario_request_rejects_unsupported_controls(body):
    with TestClient(app) as client:
        assert client.post("/api/scenarios", json=body).status_code == 422


def test_missing_configured_files_return_safe_error(monkeypatch, tmp_path):
    settings = get_settings()
    for key in ("scenario_model_file", "scenario_snapshot_file", "scenario_bundle_file"):
        monkeypatch.setattr(settings, key, str(tmp_path / "absent-secret-path"))
    monkeypatch.setattr(settings, "scenario_model_sha256", "0" * 64)
    with TestClient(app) as client:
        response = client.post("/api/scenarios", json={"country_iso3": "IND", "presets": ["growth_slowdown"]})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SCENARIO_ARTIFACT_UNAVAILABLE"
        assert "absent-secret-path" not in response.text
