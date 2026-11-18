"""Read the vetted result JSON explicitly included in an application release."""

import logging
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.schemas.prediction_bundle import PredictionBundle

PACKAGED_PREDICTIONS = Path(__file__).resolve().parents[1] / "data" / "frontend_predictions.json"
MAX_FILE_BYTES = 10 * 1024 * 1024
logger = logging.getLogger("sovereign.predictions")


@lru_cache(maxsize=4)
def _read_file(path: Path, modified_ns: int, size: int) -> PredictionBundle:
    if size > MAX_FILE_BYTES:
        raise ValueError("Prediction file exceeds size limit")
    with path.open("rb") as stream:
        content = stream.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Prediction file exceeds size limit")
    return PredictionBundle.model_validate_json(content)


def load_file_bundle(path: Path) -> PredictionBundle:
    try:
        path = path.resolve()
        stat = path.stat()
        return _read_file(path, stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError, ValidationError) as error:
        logger.warning("prediction_file_unavailable type=%s", type(error).__name__)
        raise HTTPException(503, {
            "code": "PREDICTIONS_UNAVAILABLE",
            "message": "The prediction result file is missing or invalid. Rebuild the release with valid results.",
        }) from None
