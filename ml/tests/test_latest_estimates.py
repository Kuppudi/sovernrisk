"""Synthetic data checks for inference outside the labeled training cohort."""

import json
from datetime import date

import pandas as pd
import pytest

from backend.app.schemas.prediction_bundle import PredictionBundle
from ml.default_training import FEATURES, train
from ml.features import feature_panel
from ml.latest_estimates import latest_estimates
from ml.tests.test_default_training import write_workbook


def test_features_do_not_backfill_or_carry_values_more_than_two_years():
    records = []
    for year in range(2020, 2026):
        for feature in FEATURES:
            value = None if feature == FEATURES[0] and 2021 <= year <= 2024 else year
            records.append({"country_iso3": "AAA", "observation_date": f"{year}-01-01", "indicator_code": feature, "value": value})
    snapshot = {"manifest": {"observations": records}}
    values, years = feature_panel(snapshot)
    assert values.loc[("AAA", 2022), FEATURES[0]] == 2020
    assert years.loc[("AAA", 2022), FEATURES[0]] == 2020
    assert pd.isna(values.loc[("AAA", 2023), FEATURES[0]])
    assert pd.isna(values.loc[("AAA", 2024), FEATURES[0]])
    earlier, _ = feature_panel(snapshot, through_year=2024)
    assert pd.isna(earlier.loc[("AAA", 2024), FEATURES[0]])


def test_latest_scoring_covers_unlabeled_countries_and_marks_missing_data(tmp_path):
    codes = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]
    records, labels = [], []
    for index, code in enumerate(codes):
        for year in range(1990, 2026):
            if code not in ("GGG", "HHH"):
                labels.append((code, year, 10 if (year + index) % 7 == 0 else 0))
            for column, feature in enumerate(FEATURES):
                value = (year - 1990) * (column + 1) + index
                if code == "HHH" and column >= 3:
                    value = None
                if code == "GGG" and ((column == 0 and year == 2025) or (column == 1 and year >= 2023)):
                    value = None
                records.append({"country_iso3": code, "observation_date": f"{year}-01-01", "indicator_code": feature, "value": value})
    snapshot = tmp_path / "synthetic-snapshot.json"
    snapshot.write_text(json.dumps({
        "dataset_version": "synthetic-version",
        "manifest": {"observations": records, "countries": [
            {"iso3": code, "name": f"Synthetic {code}", "region": "Test", "income_group": "Test"} for code in codes
        ]},
    }))
    workbook = tmp_path / "synthetic-labels.xlsx"
    write_workbook(workbook, labels)
    report, template, _ = train(snapshot, workbook)
    path = latest_estimates(snapshot, workbook, report, template, tmp_path / "output", date(2026, 11, 18))
    bundle = PredictionBundle.model_validate_json(path.read_bytes())
    assert bundle.schema_version == 2 and bundle.status == "latest_research"
    assert len(bundle.predictions) == len(codes)
    rows = {row.country_iso3: row for row in bundle.predictions}
    assert rows["GGG"].in_training_coverage is False
    assert rows["GGG"].risk_score is not None
    assert rows["GGG"].feature_years[FEATURES[0]] == 2024
    assert FEATURES[1] not in rows["GGG"].feature_years
    assert rows["GGG"].outcome_year == 2027 and rows["GGG"].feature_year == 2025
    assert rows["HHH"].availability == "insufficient_data" and rows["HHH"].risk_score is None
    assert rows["HHH"].observed_feature_count == 3
    metadata = json.loads((tmp_path / "output/latest_research_metadata.json").read_text())
    assert metadata["fit_through_outcome_year"] == 2025
    assert metadata["fit_rows"] > report["splits"]["train"]["rows"]
    with pytest.raises(ValueError, match="follow"):
        latest_estimates(snapshot, workbook, report, template, tmp_path / "output", date(2025, 1, 1))
