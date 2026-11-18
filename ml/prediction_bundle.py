"""Export and publish JSON results; model binaries stay off the web server."""

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

from azure.identity import AzureCliCredential
from azure.storage.blob import BlobClient, ContentSettings

from backend.app.schemas.api import CountryOut, PredictionOut
from backend.app.schemas.prediction_bundle import PredictionBundle
from backend.app.services.prediction_blobs import MAX_BUNDLE_BYTES, validate_blob_url
from ingestion.indicators import GLOBAL_INDICATORS


def export_bundle(snapshot_path: Path, output_dir: Path) -> Path:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    report = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    if report.get("status") != "retrospective_research" or report.get("features") != list(GLOBAL_INDICATORS):
        raise ValueError("Expected the nine-feature retrospective research run")
    if report["wdi_snapshot_version"] != snapshot["dataset_version"]:
        raise ValueError("Training snapshot does not match model report")
    digest = hashlib.sha256((output_dir / "research_model.joblib").read_bytes()).hexdigest()
    version = f"{report['selected_model']}-{digest[:16]}"
    generated_at = datetime.now(UTC)
    predictions = []
    with (output_dir / "historical_test_predictions.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            year = int(row["outcome_year"])
            test = report["splits"]["test"]
            if not test["first_outcome_year"] <= year <= test["last_outcome_year"]:
                raise ValueError("Prediction is outside the held-out test period")
            predictions.append(PredictionOut(
                country_iso3=row["iso3"], as_of_date=date(year - 1, 12, 31),
                outcome_year=year, feature_year=year - 2,
                risk_score=float(row["model_probability"]), downgrade_probability_12m=None,
                model_version=version, generated_at=generated_at,
                data_snapshot_id=snapshot["dataset_version"],
            ))
    bundle = PredictionBundle(
        model_version=version, dataset_version=snapshot["dataset_version"],
        generated_at=generated_at,
        limitation="Revised WDI history and an assumed reporting lag; calibration and historical-vintage validation remain incomplete. Eligible cohort requires prior-year zero default stock.",
        countries=[CountryOut.model_validate(row) for row in snapshot["manifest"]["countries"]],
        predictions=predictions,
    )
    return write_bundle(bundle, output_dir)


def write_bundle(bundle: PredictionBundle, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "frontend_predictions.json"
    # Close the temporary file before replacement so this also works on Windows.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_dir, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(bundle.model_dump_json(indent=2))
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def publish_bundle(path: Path, blob_url: str) -> str:
    """Called only by an explicit CLI publish command using the user's az login."""
    validate_blob_url(blob_url)
    content = path.read_bytes()
    if len(content) > MAX_BUNDLE_BYTES:
        raise ValueError("Prediction bundle exceeds size limit")
    PredictionBundle.model_validate_json(content)
    digest = hashlib.sha256(content).hexdigest()
    prefix, _, _ = blob_url.rpartition("/")
    archive_url = f"{prefix}/versions/{digest}.json"
    settings = ContentSettings(content_type="application/json", cache_control="no-cache")
    # Upload a complete version before replacing the single current result blob.
    with AzureCliCredential() as credential:
        with BlobClient.from_blob_url(archive_url, credential=credential) as archive:
            archive.upload_blob(content, overwrite=True, content_settings=settings)
        with BlobClient.from_blob_url(blob_url, credential=credential) as current:
            current.upload_blob(content, overwrite=True, content_settings=settings)
    return archive_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--snapshot", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("--file", type=Path, required=True)
    publish.add_argument("--blob-url", required=True)
    args = parser.parse_args()
    if args.command == "export":
        print(export_bundle(args.snapshot, args.output))
    else:
        print(f"Published research results; archived version: {publish_bundle(args.file, args.blob_url)}")


if __name__ == "__main__":
    main()
