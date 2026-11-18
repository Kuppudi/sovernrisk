"""Check what will be shipped to Azure, without deploying anything."""

import os
import json
import subprocess
import sys
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine

from backend.app.db.session import Base

from scripts.package_app_service import (
    APP_FILES,
    APP_FOLDERS,
    BUNDLED_PREDICTIONS_PATH,
    REPOSITORY_PREDICTIONS_PATH,
    PROJECT_ROOT,
    create_package,
)


@pytest.fixture
def project(tmp_path):
    for folder in APP_FOLDERS:
        (tmp_path / folder).mkdir(parents=True)
    files = [
        *APP_FILES,
        "backend/app/main.py",
        "frontend/dist/index.html",
        "frontend/dist/assets/app.js",
        "frontend/dist/maps/world-countries.json",
    ]
    for name in files:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic packaging fixture")
    return tmp_path


def test_package_contains_the_whole_app_but_not_local_secrets(project):
    for name in [
        ".env",
        "data/raw/download.json",
        "frontend/node_modules/example/index.js",
        "backend/app/__pycache__/main.pyc",
        "backend/app/.env",
        BUNDLED_PREDICTIONS_PATH,
    ]:
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Must not be deployed")

    output = project / "dist" / "app-service.zip"
    create_package(project, output)
    with ZipFile(output) as archive:
        names = archive.namelist()
    assert "backend/app/main.py" in names
    assert "frontend/dist/index.html" in names
    assert "frontend/dist/assets/app.js" in names
    assert "frontend/dist/maps/world-countries.json" in names
    assert "requirements.txt" in names and "startup.sh" in names
    assert not any(
        ".env" in name
        or "node_modules" in name
        or "__pycache__" in name
        or name.startswith("data/")
        or name == BUNDLED_PREDICTIONS_PATH
        for name in names
    )


def test_package_can_include_only_vetted_results(project, bundle_data):
    path = project / "data" / "results.json"
    path.parent.mkdir()
    bundle_data["predictions"][0]["unrecognized_field"] = "Must not ship"
    path.write_text(json.dumps(bundle_data))
    (path.parent / "research_model.joblib").write_bytes(b"Synthetic binary, not for deployment")
    output = project / "dist" / "app-service.zip"
    create_package(project, output, path)
    with ZipFile(output) as archive:
        included = json.loads(archive.read(BUNDLED_PREDICTIONS_PATH))
        assert included["predictions"][0]["risk_score"] == 0.125
        assert "unrecognized_field" not in included["predictions"][0]
        assert not any(name.endswith(".joblib") or name.startswith("data/") for name in archive.namelist())


def test_package_auto_includes_committed_results(project, bundle_data):
    path = project / REPOSITORY_PREDICTIONS_PATH
    path.parent.mkdir()
    path.write_text(json.dumps(bundle_data))
    (path.parent / "other-local-file.json").write_text('{"must_not_ship": true}')
    output = project / "dist" / "app-service.zip"
    create_package(project, output)
    with ZipFile(output) as archive:
        included = json.loads(archive.read(BUNDLED_PREDICTIONS_PATH))
        assert included["model_version"] == "synthetic-model"
        assert included["predictions"][0]["risk_score"] == 0.125
        assert not any(name.startswith("deploy/") for name in archive.namelist())
    path.write_text('{"invalid": true}')
    with pytest.raises(ValueError):
        create_package(project, output)


def test_invalid_prediction_filename_is_rejected(project, bundle_data):
    path = project / "deploy" / "frontend_prediction.json"
    path.parent.mkdir()
    path.write_text(json.dumps(bundle_data))
    with pytest.raises(ValueError, match="Rename deploy/frontend_prediction.json"):
        create_package(project, project / "dist" / "app-service.zip")


def test_invalid_prediction_file_preserves_previous_release(project):
    path = project / "invalid.json"
    path.write_text('{"invalid":true}')
    output = project / "previous.zip"
    output.write_bytes(b"Synthetic previous release")
    with pytest.raises(ValueError):
        create_package(project, output, path)
    assert output.read_bytes() == b"Synthetic previous release"


@pytest.mark.parametrize(
    "missing",
    [
        "frontend/dist/index.html",
        "frontend/dist/assets/app.js",
        "frontend/dist/maps/world-countries.json",
    ],
)
def test_incomplete_frontend_build_cannot_be_packaged(project, missing):
    (project / missing).unlink()
    with pytest.raises(ValueError):
        create_package(project, project / "dist" / "app-service.zip")


def test_package_cannot_include_itself(project):
    with pytest.raises(ValueError):
        create_package(project, project / "frontend" / "dist" / "app-service.zip")


def test_package_rejects_symlinked_source_files(project, tmp_path_factory):
    external_file = tmp_path_factory.mktemp("outside-project") / "secret.txt"
    external_file.write_text("Synthetic secret fixture")
    (project / "requirements.txt").unlink()
    (project / "requirements.txt").symlink_to(external_file)
    with pytest.raises(ValueError):
        create_package(project, project / "dist" / "app-service.zip")


def test_startup_explains_a_missing_frontend_build(tmp_path):
    script = tmp_path / "startup.sh"
    script.write_text((PROJECT_ROOT / "startup.sh").read_text())
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "Frontend build missing" in result.stderr


@pytest.mark.skipif(
    not (PROJECT_ROOT / "frontend/dist/index.html").exists(),
    reason="Run npm run build first; the App Service CI job does this.",
)
@pytest.mark.parametrize("include_predictions", [False, True])
def test_real_frontend_and_api_run_from_the_extracted_package(tmp_path, bundle_data, include_predictions, monkeypatch):
    output = tmp_path / "app-service.zip"
    results = tmp_path / "results.json" if include_predictions else None
    if results is not None:
        results.write_text(json.dumps(bundle_data))
    # Ignore any actual committed research data; this check uses synthetic inputs.
    monkeypatch.setattr("scripts.package_app_service.REPOSITORY_PREDICTIONS_PATH", "deploy/no-test-results.json")
    create_package(PROJECT_ROOT, output, results)
    unpacked = tmp_path / "unpacked"
    with ZipFile(output) as archive:
        archive.extractall(unpacked)

    # A fresh Python process verifies the packaged files, not the source checkout.
    check = """
from pathlib import Path
import os
import re
from fastapi.testclient import TestClient
import backend.app.main as server
from backend.app.services import predictions
def no_cloud_access(url):
    raise AssertionError("Packaged results must not access Blob Storage")
predictions.load_bundle = no_cloud_access
assert Path(server.__file__).resolve().is_relative_to(Path.cwd())
with TestClient(server.app) as client:
    page = client.get("/")
    assert page.status_code == 200 and "SovereignRisk AI" in page.text
    for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', page.text):
        assert client.get(asset).status_code == 200
    assert client.get("/countries/IND").text == page.text
    assert client.get("/maps/world-countries.json").status_code == 200
    model = client.get("/api/models/status").json()
    if os.environ["EXPECT_PREDICTIONS"] == "yes":
        assert model["status"] == "available" and model["research_only"] is True
        assert client.get("/api/countries/AAA/prediction").json()["risk_score"] == 0.125
        mapped = client.get("/api/data/map?indicator=default-risk&year=2025").json()
        assert [row["value"] for row in mapped["countries"]] == [0.125, None]
    else:
        assert model["status"] == "unavailable"
    assert client.get("/api/missing").status_code == 404
    assert client.get("/assets/missing.js").status_code == 404
"""
    environment = {
        **os.environ,
        "PYTHONPATH": str(unpacked),
        "FRONTEND_DIR": str(unpacked / "frontend/dist"),
        "DATABASE_URL": f"sqlite:///{tmp_path / 'synthetic-package.db'}",
        "PREDICTIONS_BLOB_URL": "",
        "PREDICTIONS_FILE": "",
        "EXPECT_PREDICTIONS": "yes" if include_predictions else "no",
    }
    engine = create_engine(environment["DATABASE_URL"])
    Base.metadata.create_all(engine)
    engine.dispose()
    result = subprocess.run(
        [sys.executable, "-c", check],
        cwd=unpacked,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
