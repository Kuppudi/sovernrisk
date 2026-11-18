"""Publish local training outputs to the application database.

Usage:
python -m ml.publish_local_predictions --output ml/artifacts/default-onset
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_engine
from backend.app.models import Country, DataSource, DataSnapshot, ModelVersion, Prediction


def load_report(output_dir: Path) -> tuple[dict, pd.DataFrame]:
    metrics_path = output_dir / "metrics.json"
    predictions_path = output_dir / "historical_test_predictions.csv"
    if not metrics_path.is_file() or not predictions_path.is_file():
        raise FileNotFoundError(
            f"Expected metrics and predictions under {output_dir}. "
            "Run ml.default_training first."
        )
    report = json.loads(metrics_path.read_text(encoding="utf-8"))
    predictions = pd.read_csv(predictions_path)
    return report, predictions


def find_snapshot_file(snapshot_id: str) -> Path:
    root = Path("data/raw")
    if not root.is_dir():
        raise FileNotFoundError("data/raw is missing. Run training first.")
    for path in root.glob("global-wdi-*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("dataset_version") == snapshot_id:
            return path
    raise FileNotFoundError(
        "Could not find a matching global WDI snapshot JSON in data/raw for the model snapshot version."
    )


def ensure_world_bank_source(db: Session) -> DataSource:
    source = db.scalar(
        select(DataSource).where(DataSource.provider_name == "World Bank WDI").limit(1)
    )
    if source is not None:
        return source
    source = DataSource(
        provider_name="World Bank WDI",
        source_url="https://api.worldbank.org/v2",
        license_notes="Public World Bank WDI source.",
        last_checked_at=datetime.now(UTC),
    )
    db.add(source)
    db.flush()
    return source


def ensure_countries_from_snapshot(db: Session, snapshot_path: Path) -> int:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    countries = payload.get("manifest", {}).get("countries", [])
    inserted = 0
    for row in countries:
        iso3 = str(row["iso3"]).upper()
        exists = db.get(Country, iso3)
        if exists is not None:
            continue
        db.add(
            Country(
                iso3=iso3,
                name=row.get("name", iso3),
                region=row.get("region", "Unknown"),
                income_group=row.get("income_group", "Unknown"),
            )
        )
        inserted += 1
    db.flush()
    return inserted


def ensure_snapshot(db: Session, snapshot_id: str) -> DataSnapshot:
    snapshot = db.get(DataSnapshot, snapshot_id)
    if snapshot is not None:
        return snapshot

    source = ensure_world_bank_source(db)

    snapshot = DataSnapshot(
        id=snapshot_id,
        source_id=source.id,
        raw_path="ml/local-training/generated-snapshot.json",
        manifest={"origin": "local-training", "created_at": datetime.now(UTC).isoformat()},
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def upsert_model_version(db: Session, output_dir: Path, report: dict) -> ModelVersion:
    snapshot_id = report["wdi_snapshot_version"]
    version = f"{report['selected_model']}-{snapshot_id[:12]}"
    model = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.model_name == "default_onset", ModelVersion.version == version)
        .limit(1)
    )
    if model is not None:
        return model

    model = ModelVersion(
        model_name="default_onset",
        version=version,
        trained_at=datetime.now(UTC),
        artifact_location=str((output_dir / "research_model.joblib").resolve()),
        evaluation_metrics=report,
        feature_schema={"features": report.get("features", [])},
    )
    db.add(model)
    db.flush()
    return model


def publish(output_dir: Path) -> tuple[str, int, int]:
    report, rows = load_report(output_dir)
    snapshot_id = report["wdi_snapshot_version"]
    snapshot_path = find_snapshot_file(snapshot_id)

    with Session(get_engine()) as db:
        ensure_world_bank_source(db)
        ensure_countries_from_snapshot(db, snapshot_path)
        ensure_snapshot(db, snapshot_id)
        model = upsert_model_version(db, output_dir, report)

        db.query(Prediction).filter(
            Prediction.model_version_id == model.id,
            Prediction.data_snapshot_id == snapshot_id,
        ).delete(synchronize_session=False)

        inserted = 0
        skipped = 0
        for row in rows.itertuples(index=False):
            iso3 = str(row.iso3).upper()
            year = int(row.outcome_year)
            risk_score = float(row.model_probability)
            exists = db.scalar(select(Country.iso3).where(Country.iso3 == iso3).limit(1))
            if exists is None:
                skipped += 1
                continue

            db.add(
                Prediction(
                    country_iso3=iso3,
                    as_of_date=date(year - 1, 12, 31),
                    model_version_id=model.id,
                    risk_score=risk_score,
                    downgrade_probability_12m=None,
                    generated_at=datetime.now(UTC),
                    data_snapshot_id=snapshot_id,
                )
            )
            inserted += 1

        db.commit()
        return model.version, inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    version, inserted, skipped = publish(args.output)
    print(
        json.dumps(
            {
                "status": "ok",
                "model_version": version,
                "predictions_inserted": inserted,
                "predictions_skipped_missing_country": skipped,
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
