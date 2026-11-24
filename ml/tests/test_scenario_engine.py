"""Synthetic frozen runs; never read or replace the user's model or scores."""

import hashlib
import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
import pytest
import sklearn
from fastapi.testclient import TestClient
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from backend.app.core.config import get_settings
from backend.app.main import app
from backend.app.schemas.scenarios import ScenarioRequest
from backend.app.services.scenarios import _load_engine
from ml.features import FEATURES
from ml.scenarios import LocalScenarioEngine, ScenarioError, content_hash


@pytest.fixture
def frozen_run(tmp_path):
    rng = np.random.default_rng(4)
    x = pd.DataFrame(rng.normal(size=(100, len(FEATURES))), columns=FEATURES)
    model = make_pipeline(SimpleImputer(strategy="median"), LogisticRegression())
    model.fit(x, x[FEATURES[0]] > 0)
    countries = [dict(iso3=code, name=f"Synthetic {code}", region="Test", income_group="Test")
                 for code in ("AAA", "BBB", "CCC")]
    records = []
    for country in countries:
        for year in range(2022, 2027):
            for index, code in enumerate(FEATURES):
                value = 0.5
                if country["iso3"] == "BBB" and code == "DT.TDS.DECT.EX.ZS":
                    value = None
                if country["iso3"] == "CCC" and index >= 3:
                    value = None
                # The growth observation is exactly two years old; future values
                # must not replace it, and carry-forward must expire after 2025.
                if code == FEATURES[0] and year in (2024, 2025):
                    value = None
                if year == 2026:
                    value = 999
                records.append(dict(country_iso3=country["iso3"], indicator_code=code,
                                    observation_date=f"{year}-01-01", value=value))
    snapshot = {"manifest": {"countries": countries, "observations": records}}
    snapshot["dataset_version"] = content_hash(snapshot["manifest"])
    snapshot_file = tmp_path / "synthetic-snapshot.json"
    snapshot_file.write_text(json.dumps(snapshot))
    metadata = dict(status="latest_research", features=FEATURES, selected_model="logistic_regression",
                    sklearn_version=sklearn.__version__, feature_lag_from_outcome_year=2,
                    max_feature_age_years=2, dataset_version=snapshot["dataset_version"],
                    as_of_date="2026-11-18", feature_year=2025, outcome_year=2027,
                    fit_through_outcome_year=2025)
    model_file = tmp_path / "synthetic-model.joblib"
    joblib.dump({"metadata": metadata, "estimator": model}, model_file)
    digest = hashlib.sha256(model_file.read_bytes()).hexdigest()
    version = f"logistic_regression-latest-{digest[:16]}"
    predictions = []
    for country in countries:
        values = {code: 0.5 for code in FEATURES}
        if country["iso3"] == "BBB":
            values["DT.TDS.DECT.EX.ZS"] = None
        if country["iso3"] == "CCC":
            values.update({code: None for code in FEATURES[3:]})
        years = {code: 2023 if code == FEATURES[0] else 2025
                 for code, value in values.items() if value is not None}
        score = float(model.predict_proba(pd.DataFrame([values]).astype(float))[0, 1]) if len(years) >= 4 else None
        predictions.append(dict(country_iso3=country["iso3"], as_of_date="2026-11-18",
                                outcome_year=2027, feature_year=2025, model_version=version,
                                data_snapshot_id=snapshot["dataset_version"],
                                generated_at=datetime.now(UTC).isoformat(), risk_score=score,
                                downgrade_probability_12m=None,
                                research_kind="latest_research", in_training_coverage=False,
                                availability="available" if score is not None else "insufficient_data",
                                observed_feature_count=len(years), feature_years=years))
    bundle = dict(schema_version=2, status="latest_research", model_version=version,
                  dataset_version=snapshot["dataset_version"], generated_at=datetime.now(UTC).isoformat(),
                  limitation="Synthetic fixture only.", feature_codes=FEATURES, max_feature_age_years=2,
                  countries=countries, predictions=predictions)
    bundle_file = tmp_path / "synthetic-bundle.json"
    bundle_file.write_text(json.dumps(bundle))
    return model_file, digest, snapshot_file, bundle_file


def test_reproduction_lag_unchanged_inputs_and_repeatability(frozen_run):
    engine = LocalScenarioEngine(*frozen_run)
    request = ScenarioRequest(country_iso3="aaa", presets=["growth_slowdown"])
    result = engine.run(request)
    assert result == engine.run(request)
    assert result.feature_year == 2025 and result.outcome_year == 2027
    features = {feature.indicator_code: feature for feature in result.features}
    growth = features[FEATURES[0]]
    assert (growth.baseline, growth.stressed, growth.source_year) == (0.5, -1.5, 2023)
    assert result.stressed_probability < result.baseline_probability
    assert result.delta_percentage_points == pytest.approx(
        100 * (result.stressed_probability - result.baseline_probability))
    assert any("decreased" in caveat for caveat in result.caveats)
    for code in FEATURES[1:]:
        assert features[code].baseline == features[code].stressed == 0.5
    assert result.baseline_reproduced and result.research_only


def test_combined_shocks_are_order_independent_and_preserve_missing_values(frozen_run):
    engine = LocalScenarioEngine(*frozen_run)
    first = engine.run(ScenarioRequest(country_iso3="BBB", presets=["growth_slowdown", "inflation_increase"]))
    second = engine.run(ScenarioRequest(country_iso3="BBB", presets=["inflation_increase", "growth_slowdown"]))
    assert first == second
    missing = next(feature for feature in first.features if feature.indicator_code == "DT.TDS.DECT.EX.ZS")
    assert missing.baseline is None and missing.stressed is None and missing.source_year is None
    assert any("outside labeled" in caveat for caveat in first.caveats)


@pytest.mark.parametrize("country,preset,error", [
    ("XXX", "growth_slowdown", "COUNTRY_NOT_FOUND"),
    ("CCC", "growth_slowdown", "INSUFFICIENT_DATA"),
    ("BBB", "debt_service_pressure", "SHOCK_INPUT_MISSING"),
])
def test_unsupported_inputs_do_not_produce_scores(frozen_run, country, preset, error):
    with pytest.raises(ScenarioError) as caught:
        LocalScenarioEngine(*frozen_run).run(ScenarioRequest(country_iso3=country, presets=[preset]))
    assert caught.value.code == error


def test_wrong_model_digest_is_rejected_before_deserialization(frozen_run, monkeypatch):
    model, _, snapshot, bundle = frozen_run
    monkeypatch.setattr(joblib, "load", lambda *args: pytest.fail("Unreviewed model was loaded"))
    with pytest.raises(ValueError, match="digest"):
        LocalScenarioEngine(model, "0" * 64, snapshot, bundle)


def test_tampered_snapshot_is_rejected_before_deserialization(frozen_run, monkeypatch):
    model, digest, snapshot, bundle = frozen_run
    data = json.loads(snapshot.read_text())
    data["manifest"]["observations"][0]["value"] = 123
    snapshot.write_text(json.dumps(data))
    monkeypatch.setattr(joblib, "load", lambda *args: pytest.fail("Model was loaded with tampered data"))
    with pytest.raises(ValueError, match="Snapshot content"):
        LocalScenarioEngine(model, digest, snapshot, bundle)


@pytest.mark.parametrize("change", ["probability", "source_year", "model_version", "dataset_version"])
def test_mismatched_baseline_and_provenance_are_rejected(frozen_run, change):
    model, digest, snapshot, bundle = frozen_run
    data = json.loads(bundle.read_text())
    if change == "probability":
        data["predictions"][0]["risk_score"] = 0.123
    elif change == "source_year":
        data["predictions"][0]["feature_years"][FEATURES[0]] = 2024
    else:
        data[change] = "mismatch"
        row_key = "data_snapshot_id" if change == "dataset_version" else change
        for row in data["predictions"]:
            row[row_key] = "mismatch"
    bundle.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        LocalScenarioEngine(model, digest, snapshot, bundle).run(
            ScenarioRequest(country_iso3="AAA", presets=["growth_slowdown"]))


@pytest.mark.parametrize("probabilities", [
    [[0, 1], [float("nan"), float("nan")]],
    [[0, 1], [-1, 2]],
    [[0, 1], [0.2, 0.2]],
    [[0, 1]],
])
def test_invalid_model_probabilities_are_rejected(frozen_run, monkeypatch, probabilities):
    engine = LocalScenarioEngine(*frozen_run)
    monkeypatch.setattr(engine.estimator, "predict_proba", lambda frame: np.array(probabilities))
    with pytest.raises(ScenarioError, match="valid probabilities"):
        engine.run(ScenarioRequest(country_iso3="AAA", presets=["inflation_increase"]))


def test_flat_response_is_preserved(frozen_run, monkeypatch):
    engine = LocalScenarioEngine(*frozen_run)
    probability = engine.bundle.predictions[0].risk_score
    monkeypatch.setattr(engine.estimator, "predict_proba",
                        lambda frame: np.array([[1 - probability, probability]] * 2))
    result = engine.run(ScenarioRequest(country_iso3="AAA", presets=["inflation_increase"]))
    assert result.delta_percentage_points == 0
    assert any("no measurable change" in caveat for caveat in result.caveats)


def test_configured_api_runs_without_database_or_cloud(frozen_run, monkeypatch):
    model, digest, snapshot, bundle = frozen_run
    settings = get_settings()
    for key, value in dict(scenario_model_file=str(model), scenario_model_sha256=digest,
                           scenario_snapshot_file=str(snapshot), scenario_bundle_file=str(bundle)).items():
        monkeypatch.setattr(settings, key, value)
    from backend.app.db.session import get_db
    def no_database():
        pytest.fail("Scenario endpoint opened SQL")
    app.dependency_overrides[get_db] = no_database
    _load_engine.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/api/scenarios", json={"country_iso3": "AAA", "presets": ["growth_slowdown"]})
            assert response.status_code == 200, response.text
            assert response.json()["baseline_reproduced"] is True
            assert client.post("/api/scenarios", json={"country_iso3": "BBB", "presets": ["debt_service_pressure"]}).status_code == 422
            assert client.post("/api/scenarios", json={"country_iso3": "XXX", "presets": ["growth_slowdown"]}).status_code == 404
    finally:
        app.dependency_overrides.clear()
        _load_engine.cache_clear()
