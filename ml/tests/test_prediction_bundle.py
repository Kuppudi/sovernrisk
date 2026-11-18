"""Synthetic file export and upload ordering. Azure clients are replaced."""

import json
from contextlib import nullcontext

import pytest

from ingestion.indicators import GLOBAL_INDICATORS
from ml import prediction_bundle


@pytest.fixture
def run_files(tmp_path):
    snapshot = tmp_path / "synthetic-snapshot.json"
    snapshot.write_text(json.dumps({
        "dataset_version": "synthetic-version",
        "manifest": {"countries": [{"iso3": "AAA", "name": "Synthetic AAA", "region": "Test", "income_group": "Test"}]},
    }))
    (tmp_path / "metrics.json").write_text(json.dumps({
        "status": "retrospective_research", "features": list(GLOBAL_INDICATORS),
        "selected_model": "synthetic", "wdi_snapshot_version": "synthetic-version",
        "splits": {"test": {"first_outcome_year": 2019, "last_outcome_year": 2025}},
    }))
    # These bytes are hashed for provenance, never deserialized as a model.
    (tmp_path / "research_model.joblib").write_bytes(b"SYNTHETIC ARTIFACT")
    (tmp_path / "historical_test_predictions.csv").write_text("iso3,outcome_year,model_probability\nAAA,2025,0.12\n")
    return snapshot, tmp_path


def test_export_keeps_years_and_preserves_previous_file_on_validation_failure(run_files):
    snapshot, output = run_files
    path = prediction_bundle.export_bundle(snapshot, output)
    before = path.read_bytes()
    bundle = json.loads(before)
    row = bundle["predictions"][0]
    assert row["outcome_year"] == 2025 and row["feature_year"] == 2023
    assert row["as_of_date"] == "2024-12-31" and row["risk_score"] == 0.12
    snapshot.write_text(snapshot.read_text().replace("synthetic-version", "wrong-version"))
    with pytest.raises(ValueError, match="snapshot"):
        prediction_bundle.export_bundle(snapshot, output)
    assert path.read_bytes() == before


def test_upload_versions_before_replacing_current_and_stops_on_failure(run_files, monkeypatch):
    snapshot, output = run_files
    path = prediction_bundle.export_bundle(snapshot, output)
    calls = []
    fail_archive = False

    class SyntheticBlob:
        def __init__(self, url):
            self.url = url

        def upload_blob(self, content, **options):
            calls.append((self.url, content))
            if fail_archive:
                raise RuntimeError("Synthetic upload failed")

    monkeypatch.setattr(prediction_bundle, "AzureCliCredential", lambda: nullcontext("synthetic-credential"))
    monkeypatch.setattr(prediction_bundle.BlobClient, "from_blob_url", lambda url, **options: nullcontext(SyntheticBlob(url)))
    url = "https://example.blob.core.windows.net/results/predictions/current.json"
    archive = prediction_bundle.publish_bundle(path, url)
    assert "/predictions/versions/" in archive
    assert [call[0] for call in calls] == [archive, url]
    assert calls[0][1] == calls[1][1] == path.read_bytes()
    calls.clear()
    fail_archive = True
    with pytest.raises(RuntimeError):
        prediction_bundle.publish_bundle(path, url)
    assert len(calls) == 1 and calls[0][0] != url
