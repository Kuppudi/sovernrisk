"""Optional local scenario integration; importing the API needs no ML extras."""

from functools import lru_cache
import logging
from pathlib import Path

from fastapi import HTTPException

from backend.app.core.config import get_settings
from backend.app.schemas.scenarios import ScenarioRequest, ScenarioResult

logger = logging.getLogger("sovereign.scenarios")


@lru_cache(maxsize=1)
def _load_engine(model: str, digest: str, snapshot: str, bundle: str):
    from ml.scenarios import LocalScenarioEngine

    return LocalScenarioEngine(Path(model), digest, Path(snapshot), Path(bundle))


def run_scenario(request: ScenarioRequest) -> ScenarioResult:
    settings = get_settings()
    configuration = (settings.scenario_model_file, settings.scenario_model_sha256,
                     settings.scenario_snapshot_file, settings.scenario_bundle_file)
    if not all(configuration):
        raise HTTPException(503, {
            "code": "SCENARIO_NOT_CONFIGURED",
            "message": "Configure a reviewed local model, its SHA-256, matching snapshot and prediction bundle.",
        })
    try:
        engine = _load_engine(*configuration)
    except Exception as exc:
        logger.warning("scenario_load_failed type=%s", type(exc).__name__)
        raise HTTPException(503, {
            "code": "SCENARIO_ARTIFACT_UNAVAILABLE",
            "message": "Local scenario artifacts or ML dependencies are unavailable or incompatible.",
        }) from None
    from ml.scenarios import ScenarioError

    try:
        return engine.run(request)
    except ScenarioError as exc:
        raise HTTPException(exc.status_code, {"code": exc.code, "message": str(exc)}) from None
    except Exception as exc:
        logger.warning("scenario_inference_failed type=%s", type(exc).__name__)
        raise HTTPException(503, {
            "code": "SCENARIO_INFERENCE_FAILED", "message": "Local scenario inference failed.",
        }) from None
