"""Local conditional scenario inference using a trusted, frozen research run.

No training, network access or writes occur here. The reviewed model hash must
come from the operator; request bodies cannot select files or upload artifacts.
"""

import hashlib
import io
import json
import math
import re
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

from backend.app.schemas.prediction_bundle import PredictionBundle
from backend.app.schemas.scenarios import (
    POLICY_VERSION, PRESETS, ScenarioFeature, ScenarioRequest, ScenarioResult,
)
from ingestion.indicators import GLOBAL_INDICATORS
from ml.features import FEATURES, MAX_FEATURE_AGE, feature_panel


class ScenarioError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def content_hash(value: dict) -> str:
    content = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(content.encode()).hexdigest()


class LocalScenarioEngine:
    def __init__(self, model_path: Path, model_sha256: str,
                 snapshot_path: Path, bundle_path: Path):
        if not re.fullmatch(r"[a-f0-9]{64}", model_sha256):
            raise ValueError("A reviewed SHA-256 model digest is required")
        model_bytes = model_path.read_bytes()
        if hashlib.sha256(model_bytes).hexdigest() != model_sha256:
            raise ValueError("Model digest does not match the reviewed artifact")
        bundle_bytes = bundle_path.read_bytes()
        self.bundle = PredictionBundle.model_validate_json(bundle_bytes)
        if self.bundle.status != "latest_research":
            raise ValueError("Scenarios require the latest research bundle")
        snapshot = json.loads(snapshot_path.read_bytes())
        if content_hash(snapshot["manifest"]) != snapshot["dataset_version"]:
            raise ValueError("Snapshot content does not match its version")
        if snapshot["dataset_version"] != self.bundle.dataset_version:
            raise ValueError("Snapshot and prediction bundle do not match")
        # A hash establishes integrity, not trust. Only operator-reviewed local
        # artifacts may reach this point; joblib deserialization can execute code.
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            artifact = joblib.load(io.BytesIO(model_bytes))
        metadata = artifact["metadata"]
        self.estimator = artifact["estimator"]
        if metadata["sklearn_version"] != sklearn.__version__:
            raise ValueError("Use the scikit-learn version recorded by training")
        if (metadata["status"] != "latest_research"
                or metadata["features"] != FEATURES
                or metadata["feature_lag_from_outcome_year"] != 2
                or metadata["max_feature_age_years"] != MAX_FEATURE_AGE
                or self.bundle.max_feature_age_years != MAX_FEATURE_AGE
                or metadata["dataset_version"] != self.bundle.dataset_version):
            raise ValueError("Model feature policy or provenance does not match")
        self.model_version = f"{metadata['selected_model']}-latest-{model_sha256[:16]}"
        if self.model_version != self.bundle.model_version:
            raise ValueError("Model artifact and prediction bundle do not match")
        if list(self.estimator.classes_) != [0, 1]:
            raise ValueError("Model must expose the binary default-onset classes")
        if list(self.estimator.feature_names_in_) != FEATURES:
            raise ValueError("Model feature order does not match the research schema")
        for row in self.bundle.predictions:
            if (row.as_of_date.isoformat() != metadata["as_of_date"]
                    or row.feature_year != metadata["feature_year"]
                    or row.outcome_year != metadata["outcome_year"]
                    or metadata["fit_through_outcome_year"] >= row.as_of_date.year):
                raise ValueError("Model dates do not match the latest prediction bundle")
        if metadata["feature_year"] != metadata["outcome_year"] - 2:
            raise ValueError("Scenario inference must preserve the two-year outcome lag")
        for record in snapshot["manifest"]["observations"]:
            value = record["value"]
            if value is not None and (isinstance(value, bool)
                                      or not isinstance(value, (int, float))
                                      or not math.isfinite(value)):
                raise ValueError("Snapshot contains a non-finite or non-numeric observation")
        self.inputs, self.years = feature_panel(snapshot, through_year=metadata["feature_year"])
        self.feature_year = metadata["feature_year"]
        self.model_sha256 = model_sha256
        self.bundle_sha256 = hashlib.sha256(bundle_bytes).hexdigest()

    def run(self, request: ScenarioRequest) -> ScenarioResult:
        row = next((row for row in self.bundle.predictions
                    if row.country_iso3 == request.country_iso3), None)
        if row is None:
            raise ScenarioError("COUNTRY_NOT_FOUND", "Country is absent from the frozen run", 404)
        if row.risk_score is None or (request.country_iso3, self.feature_year) not in self.inputs.index:
            raise ScenarioError("INSUFFICIENT_DATA", "At least four recent model features are required")
        baseline = self.inputs.loc[[(request.country_iso3, self.feature_year)], FEATURES].copy()
        years = self.years.loc[(request.country_iso3, self.feature_year)]
        actual_years = {code: int(year) for code, year in years.dropna().items()}
        if actual_years != row.feature_years or int(baseline.notna().sum(axis=1).iloc[0]) != row.observed_feature_count:
            raise ScenarioError("BASELINE_MISMATCH", "Input coverage does not reproduce the frozen run", 503)
        selected = [preset for preset in PRESETS if preset.id in request.presets]
        stressed = baseline.copy()
        for preset in selected:
            value = baseline.iloc[0][preset.indicator_code]
            if pd.isna(value):
                raise ScenarioError("SHOCK_INPUT_MISSING", f"No recent input for {preset.indicator_code}")
            stressed.loc[:, preset.indicator_code] += preset.delta_percentage_points
        probabilities = self.estimator.predict_proba(pd.concat([baseline, stressed]))
        probabilities = np.asarray(probabilities)
        if (probabilities.shape != (2, 2) or not np.isfinite(probabilities).all()
                or (probabilities < 0).any() or (probabilities > 1).any()
                or not np.allclose(probabilities.sum(axis=1), 1)):
            raise ScenarioError("INVALID_MODEL_OUTPUT", "Model did not return valid probabilities", 503)
        before, after = map(float, probabilities[:, 1])
        if not math.isclose(before, row.risk_score, rel_tol=1e-9, abs_tol=1e-10):
            raise ScenarioError("BASELINE_MISMATCH", "Model does not reproduce the frozen baseline", 503)
        changes = {preset.indicator_code: preset.delta_percentage_points for preset in selected}
        features = []
        for code in FEATURES:
            value = baseline.iloc[0][code]
            changed = stressed.iloc[0][code]
            features.append(ScenarioFeature(
                indicator_code=code, unit=GLOBAL_INDICATORS[code]["unit"],
                source_year=actual_years.get(code),
                baseline=None if pd.isna(value) else float(value),
                stressed=None if pd.isna(changed) else float(changed),
                delta_percentage_points=changes.get(code),
            ))
        caveats = [
            "Conditional research sensitivity, not a causal policy effect or validated forecast.",
            "Assumes no ongoing default; current default status has not been verified.",
            "Preset magnitudes are illustrative demo assumptions, not country-calibrated limits.",
            "Other features are held fixed; economic transmission and feedback are not modeled.",
            "Revised historical inputs use the frozen snapshot, not current report forecasts.",
            "Calibration and uncertainty intervals are unavailable.",
        ]
        if len(actual_years) < len(FEATURES):
            caveats.append("Missing features remain missing and use the fitted model's existing handling.")
        if any(year < self.feature_year for year in actual_years.values()):
            caveats.append("Some inputs are carried forward by at most two years; source years are shown.")
        if not row.in_training_coverage:
            caveats.append("Country lies outside labeled training coverage.")
        if abs(after - before) <= 1e-12:
            caveats.append("The model returns no measurable change for these shocks.")
        elif after < before:
            caveats.append("The stressed estimate decreased; the model is not constrained to monotonic responses.")
        identity = {
            "policy_version": POLICY_VERSION, "country_iso3": request.country_iso3,
            "presets": [preset.model_dump() for preset in selected], "model_sha256": self.model_sha256,
            "dataset_version": self.bundle.dataset_version, "bundle_sha256": self.bundle_sha256,
        }
        return ScenarioResult(
            scenario_id=content_hash(identity), country_iso3=row.country_iso3,
            as_of_date=row.as_of_date, feature_year=self.feature_year, outcome_year=row.outcome_year,
            model_version=self.model_version, model_sha256=self.model_sha256,
            dataset_version=self.bundle.dataset_version, bundle_sha256=self.bundle_sha256,
            baseline_probability=before, stressed_probability=after,
            delta_percentage_points=(after - before) * 100,
            observed_feature_count=len(actual_years), in_training_coverage=row.in_training_coverage,
            presets=selected, features=features, caveats=caveats,
        )
