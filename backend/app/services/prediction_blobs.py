"""Read small, validated result bundles; never load a model in a web request."""

import logging
import time
from functools import lru_cache
from urllib.parse import urlsplit

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.schemas.prediction_bundle import PredictionBundle

logger = logging.getLogger("sovereign.predictions")
MAX_BUNDLE_BYTES = 10 * 1024 * 1024


def validate_blob_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".blob.core.windows.net")
        or parsed.username or parsed.password or parsed.port
        or parsed.query or parsed.fragment
        or len(parsed.path.strip("/").split("/")) < 2
    ):
        raise ValueError("Use a private Azure Blob HTTPS URL without a SAS token")
    return url


@lru_cache(maxsize=2)
def blob_client(url: str) -> BlobClient:
    return BlobClient.from_blob_url(
        validate_blob_url(url), credential=DefaultAzureCredential(),
        connection_timeout=5, read_timeout=15, retry_total=2,
    )


@lru_cache(maxsize=4)
def _read_bundle(url: str, minute: int) -> PredictionBundle:
    content = blob_client(url).download_blob(length=MAX_BUNDLE_BYTES + 1).readall()
    if len(content) > MAX_BUNDLE_BYTES:
        raise ValueError("Prediction bundle exceeds size limit")
    return PredictionBundle.model_validate_json(content)


def load_bundle(url: str) -> PredictionBundle:
    try:
        return _read_bundle(url, int(time.time() // 60))
    except (AzureError, ValidationError, ValueError, OSError) as error:
        logger.warning("prediction_bundle_unavailable type=%s", type(error).__name__)
        raise HTTPException(503, {
            "code": "PREDICTIONS_UNAVAILABLE",
            "message": "Prediction results are unavailable. Check the Blob file and managed identity access.",
        }) from None
