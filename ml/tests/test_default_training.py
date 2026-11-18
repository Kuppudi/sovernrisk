"""Isolated synthetic checks for labels, forecast timing and notebook execution."""

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest
from openpyxl import Workbook

from ml.default_training import (
    FEATURES,
    TARGET,
    build_panel,
    chronological_splits,
    read_default_labels,
)


def write_workbook(path, observations):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Debt_2026.csv"
    sheet.append(["Synthetic test fixture; never production labels"])
    sheet.append(["k3", "DEBT_YEAR", "DEBT_TOTAL_2026"])
    for code, year, stock in observations:
        sheet.append([f"{code}_{year}", year, stock])
    workbook.save(path)
    workbook.close()


def test_labels_require_explicit_prior_zero_and_exclude_ongoing_defaults(tmp_path):
    path = tmp_path / "synthetic-labels.xlsx"
    write_workbook(path, [
        ("AAA", 2010, 0), ("AAA", 2011, 12), ("AAA", 2012, 15),
        ("AAA", 2013, 0), ("AAA", 2014, 0),
        ("BBB", 2011, 10),  # Prior status absent.
        ("CCC", 2010, -1), ("CCC", 2011, 10),
        ("DDD", 2010, 0), ("DDD", 2012, 10),  # Gap is not zero.
    ])
    labels = read_default_labels(path)
    assert list(labels[["iso3", "outcome_year", TARGET]].itertuples(index=False, name=None)) == [
        ("AAA", 2011, True), ("AAA", 2014, False),
    ]
    assert labels.attrs["excluded_negative_stocks"] == 1


def test_panel_uses_lagged_features_and_rejects_insufficient_coverage(tmp_path):
    observations = []
    for code in ("AAA", "BBB"):
        for year in (2010, 2011, 2012):
            for index, feature in enumerate(FEATURES):
                observations.append({
                    "country_iso3": code,
                    "observation_date": f"{year}-01-01",
                    "indicator_code": feature,
                    "value": None if code == "BBB" and index >= 3 else year,
                })
    path = tmp_path / "synthetic-snapshot.json"
    path.write_text(json.dumps({
        "dataset_version": "synthetic-version",
        "manifest": {"observations": observations},
    }))
    labels = pd.DataFrame({
        "iso3": ["AAA", "BBB"], "outcome_year": [2012, 2012], TARGET: [True, False],
    })
    panel, version = build_panel(path, labels)
    assert version == "synthetic-version"
    assert panel["iso3"].tolist() == ["AAA"]
    assert panel.iloc[0][FEATURES].tolist() == [2010] * len(FEATURES)


def test_time_splits_keep_periods_separate_and_require_both_classes():
    rows = pd.DataFrame({
        "outcome_year": [2013, 2013, 2014, 2018, 2019, 2025],
        TARGET: [False, True, False, True, False, True],
    })
    splits = chronological_splits(rows, 2013, 2018)
    assert splits["train"]["outcome_year"].max() == 2013
    assert splits["validation"]["outcome_year"].tolist() == [2014, 2018]
    assert splits["test"]["outcome_year"].tolist() == [2019, 2025]
    with pytest.raises(ValueError, match="cutoff"):
        chronological_splits(rows, 2018, 2013)
    with pytest.raises(ValueError, match="test must contain both"):
        chronological_splits(rows.iloc[:-1], 2013, 2018)


def test_notebook_trains_and_exports_only_research_outputs(tmp_path, monkeypatch):
    """Run the user entry point against fabricated files, without API/cloud calls."""
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "synthetic-snapshot.json"
    workbook = tmp_path / "synthetic-labels.xlsx"
    output = tmp_path / "research-output"
    observations = []
    stocks = []
    for index, code in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")):
        for year in range(1990, 2026):
            stocks.append((code, year, 10 if (year + index) % 7 == 0 else 0))
            for feature_index, feature in enumerate(FEATURES):
                observations.append({
                    "country_iso3": code,
                    "observation_date": f"{year}-01-01",
                    "indicator_code": feature,
                    "value": (year - 1990) * (feature_index + 1) + index,
                })
    write_workbook(workbook, stocks)
    snapshot.write_text(json.dumps({
        "dataset_version": "synthetic-notebook-version",
        "manifest": {
            "observations": observations,
            "countries": [
                {"iso3": code, "name": f"Synthetic {code}", "region": "Test", "income_group": "Test"}
                for code in ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")
            ],
        },
    }))
    monkeypatch.setenv("WDI_SNAPSHOT", str(snapshot))
    monkeypatch.setenv("DEFAULT_WORKBOOK", str(workbook))
    monkeypatch.setenv("DEFAULT_MODEL_OUTPUT", str(output))
    monkeypatch.chdir(repo)
    notebook = json.loads((repo / "notebooks/default_training.ipynb").read_text())
    namespace = {}
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None
            exec(compile("".join(cell["source"]), f"notebook-cell-{index}", "exec"), namespace)

    report = json.loads((output / "metrics.json").read_text())
    predictions = pd.read_csv(output / "historical_test_predictions.csv")
    artifact = joblib.load(output / "research_model.joblib")
    assert report["status"] == "retrospective_research"
    assert report["wdi_snapshot_version"] == "synthetic-notebook-version"
    assert report["splits"]["train"]["last_outcome_year"] == 2013
    assert report["splits"]["validation"]["last_outcome_year"] == 2018
    assert predictions["outcome_year"].min() == 2019
    assert predictions["outcome_year"].max() == 2025
    assert predictions["model_probability"].between(0, 1).all()
    assert set(report["validation"]) == {"event_rate", "logistic_regression", "gradient_boosting"}
    assert artifact["metadata"] == report
    assert len(artifact["estimator"].predict_proba(pd.DataFrame([dict.fromkeys(FEATURES, 1)]))) == 1
    from ml.prediction_bundle import export_bundle
    from backend.app.schemas.prediction_bundle import PredictionBundle

    exported = PredictionBundle.model_validate_json(export_bundle(snapshot, output).read_bytes())
    assert len(exported.predictions) == len(predictions)
    assert exported.predictions[0].model_version == exported.model_version
    assert max(row.outcome_year for row in exported.predictions) == 2025
