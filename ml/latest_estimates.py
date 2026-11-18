"""Refit the selected research learner and score the full economic catalog."""

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import joblib
from sklearn.base import clone

from backend.app.schemas.api import CountryOut, PredictionOut
from backend.app.schemas.prediction_bundle import PredictionBundle
from ml.default_training import FEATURES, MIN_FEATURES, TARGET, build_panel, read_default_labels
from ml.features import MAX_FEATURE_AGE, feature_panel
from ml.prediction_bundle import write_bundle


def latest_estimates(snapshot_path: Path, workbook: Path, report: dict, template, output: Path, as_of: date) -> Path:
    if as_of.year <= report["splits"]["test"]["last_outcome_year"]:
        raise ValueError("Latest scoring date must follow the completed evaluation years")
    if report.get("max_feature_age_years") != MAX_FEATURE_AGE:
        raise ValueError("Re-evaluate training with the current historical feature policy")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if report["wdi_snapshot_version"] != snapshot["dataset_version"]:
        raise ValueError("Training report and scoring snapshot do not match")
    rows, _ = build_panel(snapshot_path, read_default_labels(workbook))
    rows = rows.loc[rows["outcome_year"] < as_of.year]
    if rows[TARGET].nunique() != 2:
        raise ValueError("Research fit requires both outcome classes")
    # Selection and reported test metrics belong to the earlier chronological run.
    # Refit only after evaluation; do not report those metrics as testing this fit.
    estimator = clone(template)
    estimator.fit(rows[FEATURES], rows[TARGET])
    feature_year = as_of.year - 1
    outcome_year = feature_year + 2
    panel, years = feature_panel(snapshot, through_year=feature_year)
    inputs = panel.xs(feature_year, level="feature_year")
    source_years = years.xs(feature_year, level="feature_year")
    eligible = inputs.notna().sum(axis=1) >= MIN_FEATURES
    probabilities = dict(zip(inputs.index[eligible], estimator.predict_proba(inputs.loc[eligible, FEATURES])[:, 1])) if eligible.any() else {}
    generated = datetime.now(UTC)
    countries = [CountryOut.model_validate(row) for row in snapshot["manifest"]["countries"]]
    fitted_countries = set(rows["iso3"])
    metadata = {
        "status": "latest_research", "dataset_version": snapshot["dataset_version"],
        "as_of_date": as_of.isoformat(), "feature_year": feature_year,
        "outcome_year": outcome_year, "features": FEATURES,
        "max_feature_age_years": MAX_FEATURE_AGE,
        "fit_rows": len(rows), "fit_through_outcome_year": int(rows["outcome_year"].max()),
        "fit_issuers": len(fitted_countries), "selected_model": report["selected_model"],
        "scored_countries": sum(country.iso3 in probabilities for country in countries),
        "catalog_countries": len(countries),
        "label_source": report["label_source"], "label_url": report["label_url"],
        "label_workbook_sha256": report["label_workbook_sha256"],
        "sklearn_version": report["sklearn_version"],
        "feature_lag_from_outcome_year": report["feature_lag_from_outcome_year"],
        "evaluation_note": "Chronological test metrics are in metrics.json and describe the pre-refit experiment. This full-history fit is not separately backtested.",
        "prior_default_assumption": "No ongoing default at forecast origin; current default status is not verified.",
    }
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / "latest_research_model.joblib"
    joblib.dump({"metadata": metadata, "estimator": estimator}, artifact)
    version = f"{report['selected_model']}-latest-{hashlib.sha256(artifact.read_bytes()).hexdigest()[:16]}"
    predictions = []
    for country in countries:
        observed = source_years.loc[country.iso3].dropna().to_dict() if country.iso3 in source_years.index else {}
        observed = {code: int(year) for code, year in observed.items()}
        score = probabilities.get(country.iso3)
        predictions.append(PredictionOut(
            country_iso3=country.iso3, as_of_date=as_of, outcome_year=outcome_year,
            feature_year=feature_year, risk_score=float(score) if score is not None else None,
            downgrade_probability_12m=None, model_version=version,
            generated_at=generated, data_snapshot_id=snapshot["dataset_version"],
            research_kind="latest_research", observed_feature_count=len(observed),
            feature_years=observed, in_training_coverage=country.iso3 in fitted_countries,
            availability="available" if score is not None else "insufficient_data",
        ))
    (output / "latest_research_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    bundle = PredictionBundle(
        schema_version=2, status="latest_research", model_version=version,
        dataset_version=snapshot["dataset_version"], generated_at=generated,
        feature_codes=FEATURES, max_feature_age_years=MAX_FEATURE_AGE,
        limitation="Conditional research estimates of conventional sovereign default onset, assuming no ongoing default at forecast origin. Current default status is unverified. Revised history, limited labeled-country coverage and incomplete calibration limit accuracy. Inputs may use observations up to two years before the feature reference year.",
        countries=countries, predictions=predictions,
    )
    return write_bundle(bundle, output)
