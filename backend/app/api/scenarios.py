"""One-country scenario endpoints, independent of SQL and cloud services."""

from fastapi import APIRouter

from backend.app.schemas.scenarios import PRESETS, ScenarioRequest, ScenarioResult, ShockPreset
from backend.app.services.scenarios import run_scenario

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


@router.get("/presets", response_model=list[ShockPreset])
def presets():
    return PRESETS


@router.post("", response_model=ScenarioResult)
def simulate(body: ScenarioRequest):
    return run_scenario(body)
