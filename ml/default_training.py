"""Reproduce a retrospective sovereign default-onset experiment offline."""

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from openpyxl import load_workbook
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

from ingestion.indicators import GLOBAL_INDICATORS

FEATURES = list(GLOBAL_INDICATORS)
MIN_FEATURES = 4
# Forecast made at the end of year Y-1 for an outcome during year Y.
# Use observations from Y-2 to leave a publication lag.
FEATURE_LAG = 2
TARGET = "default_onset"
LABEL_SOURCE = "BoC–BoE Sovereign Default Database, 2026 edition (conventional debt)"
LABEL_URL = "https://www.bankofcanada.ca/2026/10/staff-analytical-paper-2026-48/"


def read_default_labels(path: Path) -> pd.DataFrame:
    """Compare consecutive numeric conventional debt-in-default stocks."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = workbook["Debt_2026.csv"].values
        for row in rows:
            if {"k3", "DEBT_YEAR", "DEBT_TOTAL_2026"} <= set(row):
                key = row.index("k3")
                year_column = row.index("DEBT_YEAR")
                stock = row.index("DEBT_TOTAL_2026")
                break
        else:
            raise ValueError("2026 default workbook observation headers not found")

        observations = []
        negative_values = 0
        for row in rows:
            if not isinstance(row[key], str) or not isinstance(row[year_column], int):
                continue
            code, _, year_text = row[key].rpartition("_")
            year = row[year_column]
            if len(code) != 3 or not code.isalpha() or year_text != str(year):
                continue
            if year > 2025 or not isinstance(row[stock], (int, float)):
                continue
            if row[stock] < 0:
                negative_values += 1
                continue
            observations.append((code.upper(), year, float(row[stock])))
    finally:
        workbook.close()

    panel = pd.DataFrame(observations, columns=["iso3", "outcome_year", "in_default"])
    panel["in_default"] = panel["in_default"] > 0
    prior = panel.loc[~panel["in_default"], ["iso3", "outcome_year"]].copy()
    prior["outcome_year"] += 1
    # Skip issuer-years with unknown prior status or an ongoing default.
    labels = panel.merge(prior, on=["iso3", "outcome_year"], validate="one_to_one")
    labels = labels.rename(columns={"in_default": TARGET})
    labels.attrs["excluded_negative_stocks"] = negative_values
    return labels


def build_panel(path: Path, labels: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    manifest = snapshot["manifest"]
    observations = pd.DataFrame(manifest["observations"])
    observations = observations.loc[observations["indicator_code"].isin(FEATURES)]
    wide = observations.pivot(
        index=["country_iso3", "observation_date"],
        columns="indicator_code",
        values="value",
    ).reset_index()
    missing = set(FEATURES) - set(wide.columns)
    if missing:
        raise ValueError(
            f"Snapshot missing training indicators: {', '.join(sorted(missing))}"
        )
    wide["outcome_year"] = (
        pd.to_datetime(wide["observation_date"]).dt.year + FEATURE_LAG
    )
    wide = wide.rename(columns={"country_iso3": "iso3"})
    rows = wide.merge(labels, on=["iso3", "outcome_year"], validate="one_to_one")
    rows = rows.loc[rows[FEATURES].notna().sum(axis=1) >= MIN_FEATURES]
    return rows.sort_values(["outcome_year", "iso3"]), snapshot["dataset_version"]


def chronological_splits(
    rows: pd.DataFrame, train_through: int, validate_through: int
) -> dict[str, pd.DataFrame]:
    if train_through >= validate_through:
        raise ValueError("Training cutoff must precede the validation cutoff")
    year = rows["outcome_year"]
    splits = {
        "train": rows.loc[year <= train_through],
        "validation": rows.loc[(year > train_through) & (year <= validate_through)],
        "test": rows.loc[year > validate_through],
    }
    for name, split in splits.items():
        if split[TARGET].nunique() != 2:
            raise ValueError(f"{name} must contain both onset and non-onset rows")
    return splits


def validation_threshold(y, probability) -> float:
    precision, recall, thresholds = precision_recall_curve(y, probability)
    denom = (precision[:-1] + recall[:-1]).clip(1e-12, None)
    f1 = 2 * precision[:-1] * recall[:-1] / denom
    return float(thresholds[f1.argmax()])


def metrics(y, probability, threshold: float) -> dict:
    return {
        "average_precision": float(average_precision_score(y, probability)),
        "roc_auc": float(roc_auc_score(y, probability)),
        "brier_score": float(brier_score_loss(y, probability)),
        "confusion_matrix": confusion_matrix(
            y, probability >= threshold, labels=[False, True]
        ).tolist(),
    }


def train(snapshot: Path, workbook: Path, train_through=2013, validate_through=2018):
    labels = read_default_labels(workbook)
    rows, snapshot_version = build_panel(snapshot, labels)
    splits = chronological_splits(rows, train_through, validate_through)
    training = splits["train"]
    validation = splits["validation"]
    test = splits["test"]
    if training[FEATURES].notna().sum().eq(0).any():
        raise ValueError(
            "At least one feature has no reported values in training years"
        )
    models = {
        "event_rate": DummyClassifier(strategy="prior"),
        "logistic_regression": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            RobustScaler(),
            LogisticRegression(max_iter=1000),
        ),
        "gradient_boosting": HistGradientBoostingClassifier(
            max_iter=60,
            max_leaf_nodes=7,
            min_samples_leaf=60,
            l2_regularization=1,
            early_stopping=False,
            random_state=42,
        ),
    }

    validation_scores = {}
    thresholds = {}
    for name, model in models.items():
        model.fit(training[FEATURES], training[TARGET])
        probability = model.predict_proba(validation[FEATURES])[:, 1]
        thresholds[name] = validation_threshold(validation[TARGET], probability)
        validation_scores[name] = metrics(
            validation[TARGET], probability, thresholds[name]
        )

    selected = max(
        validation_scores, key=lambda name: validation_scores[name]["average_precision"]
    )
    model = models[selected]
    threshold = thresholds[selected]
    predictions = test[["iso3", "outcome_year", TARGET]].copy()
    predictions["model_probability"] = model.predict_proba(test[FEATURES])[:, 1]
    predictions["predicted_onset"] = predictions["model_probability"] >= threshold
    baseline = models["event_rate"].predict_proba(test[FEATURES])[:, 1]
    with workbook.open("rb") as source:
        workbook_hash = hashlib.file_digest(source, "sha256").hexdigest()
    report = {
        "status": "retrospective_research",
        "label_source": LABEL_SOURCE,
        "label_url": LABEL_URL,
        "label_workbook_sha256": workbook_hash,
        "wdi_snapshot_version": snapshot_version,
        "vintage_limitation": "Current revised WDI history. Historical publication timing is unverified.",
        "cohort": "Issuers matched to WDI with numeric prior and outcome debt stocks, no prior default, and at least four economic features.",
        "features": FEATURES,
        "feature_lag_from_outcome_year": FEATURE_LAG,
        "sklearn_version": sklearn.__version__,
        "splits": {
            name: {
                "first_outcome_year": int(split["outcome_year"].min()),
                "last_outcome_year": int(split["outcome_year"].max()),
                "rows": len(split),
                "issuers": int(split["iso3"].nunique()),
                "onsets": int(split[TARGET].sum()),
            }
            for name, split in splits.items()
        },
        "matched_issuers": int(rows["iso3"].nunique()),
        "excluded_negative_label_values": labels.attrs["excluded_negative_stocks"],
        "selected_model": selected,
        "threshold_from_validation": threshold,
        "validation": validation_scores,
        "test": {
            "selected_model": metrics(
                test[TARGET], predictions["model_probability"], threshold
            ),
            "event_rate": metrics(test[TARGET], baseline, thresholds["event_rate"]),
        },
    }
    return report, model, predictions


def save_run(directory: Path, report: dict, model, predictions: pd.DataFrame) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    predictions.to_csv(directory / "historical_test_predictions.csv", index=False)
    joblib.dump(
        {"metadata": report, "estimator": model}, directory / "research_model.joblib"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--default-workbook", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report, model, predictions = train(args.snapshot, args.default_workbook)
    save_run(args.output, report, model, predictions)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
