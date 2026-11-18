"""Create a source ZIP for Azure App Service. Run after building the frontend."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# An explicit list keeps credentials, local data, and node_modules out of the ZIP.
APP_FOLDERS = ("backend/app", "backend/alembic", "ingestion", "frontend/dist")
APP_FILES = (
    "backend/__init__.py",
    "requirements.txt",
    "requirements.lock",
    "pyproject.toml",
    "alembic.ini",
    "startup.sh",
)
BUNDLED_PREDICTIONS_PATH = "backend/app/data/frontend_predictions.json"
REPOSITORY_PREDICTIONS_PATH = "deploy/frontend_predictions.json"


def prediction_payload(path: Path) -> bytes:
    # Keep ordinary CI packaging standard-library-only. The optional result
    # path is used from the training environment, where app dependencies exist.
    import sys

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from backend.app.schemas.prediction_bundle import PredictionBundle

    with path.open("rb") as stream:
        content = stream.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Prediction bundle exceeds size limit")
    bundle = PredictionBundle.model_validate_json(content)
    # Serialize the allowed fields, excluding unknown nested input properties.
    return bundle.model_dump_json().encode("utf-8")


def create_package(project: Path, output: Path, predictions_file: Path | None = None) -> None:
    if predictions_file is None:
        if (project / "deploy/frontend_prediction.json").exists():
            raise ValueError(
                "Rename deploy/frontend_prediction.json to deploy/frontend_predictions.json so the results are included."
            )
        candidate = project / REPOSITORY_PREDICTIONS_PATH
        if candidate.is_symlink():
            raise ValueError("Repository prediction JSON must be a regular file, not a symlink")
        if candidate.exists():
            predictions_file = candidate
    results = prediction_payload(predictions_file) if predictions_file is not None else None
    for folder in APP_FOLDERS:
        if output.resolve().is_relative_to((project / folder).resolve()):
            raise ValueError(
                "Put the ZIP outside the application folders, for example dist/app-service.zip."
            )
    required = ("frontend/dist/index.html", "frontend/dist/maps/world-countries.json")
    for name in (*APP_FILES, *required):
        if not (project / name).is_file():
            raise ValueError(
                f"Required file missing: {name}. Build the frontend first."
            )

    files = [project / name for name in APP_FILES]
    for folder in APP_FOLDERS:
        directory = project / folder
        if not directory.is_dir():
            raise ValueError(f"Required folder missing: {folder}")
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(project)
            if relative.as_posix() == BUNDLED_PREDICTIONS_PATH:
                continue  # Only the validated, allowlisted result source is packaged.
            if "__pycache__" in relative.parts or any(
                part.startswith(".") for part in relative.parts
            ):
                continue
            if path.suffix in (".pyc", ".pyo"):
                continue
            files.append(path)

    if not any(path.parent.name == "assets" and path.suffix == ".js" for path in files):
        raise ValueError("Frontend JavaScript missing. Run npm run build first.")

    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(project.resolve()):
            raise ValueError(
                f"Deployment files must stay inside the project: {path.relative_to(project)}"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(project).as_posix())
        if results is not None:
            archive.writestr(BUNDLED_PREDICTIONS_PATH, results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "dist" / "app-service.zip"
    )
    parser.add_argument(
        "--predictions-file", type=Path,
        help="Include vetted frontend_predictions.json from local training in this release.",
    )
    args = parser.parse_args()
    try:
        create_package(PROJECT_ROOT, args.output, args.predictions_file)
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(f"App Service package: {args.output}")
    if args.predictions_file is not None or (PROJECT_ROOT / REPOSITORY_PREDICTIONS_PATH).is_file():
        print("Included historical research results. Blob access is not required to serve them.")


if __name__ == "__main__":
    main()
