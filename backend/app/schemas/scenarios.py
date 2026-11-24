"""Phase 1 scenario contract, usable without installing the ML runtime."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.api import ISO3

PresetId = Literal["growth_slowdown", "inflation_increase", "debt_service_pressure"]
POLICY_VERSION = "scenario-presets-v1"


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country_iso3: ISO3
    presets: list[PresetId] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_presets(self):
        if len(set(self.presets)) != len(self.presets):
            raise ValueError("Select each preset at most once")
        return self


class ShockPreset(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: PresetId
    label: str
    indicator_code: str
    delta_percentage_points: float


PRESETS = (
    ShockPreset(id="growth_slowdown", label="Growth slowdown",
                indicator_code="NY.GDP.MKTP.KD.ZG", delta_percentage_points=-2),
    ShockPreset(id="inflation_increase", label="Inflation increase",
                indicator_code="FP.CPI.TOTL.ZG", delta_percentage_points=3),
    ShockPreset(id="debt_service_pressure", label="Debt-service pressure",
                indicator_code="DT.TDS.DECT.EX.ZS", delta_percentage_points=5),
)


class ScenarioFeature(BaseModel):
    indicator_code: str
    unit: str
    source_year: int | None
    baseline: float | None = Field(allow_inf_nan=False)
    stressed: float | None = Field(allow_inf_nan=False)
    delta_percentage_points: float | None = None


class ScenarioResult(BaseModel):
    schema_version: Literal[1] = 1
    scenario_id: str
    policy_version: str = POLICY_VERSION
    country_iso3: str
    as_of_date: date
    feature_year: int
    outcome_year: int
    model_version: str
    model_sha256: str
    dataset_version: str
    bundle_sha256: str
    baseline_probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    stressed_probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    delta_percentage_points: float = Field(allow_inf_nan=False)
    baseline_reproduced: Literal[True] = True
    research_only: Literal[True] = True
    observed_feature_count: int
    in_training_coverage: bool
    presets: list[ShockPreset]
    features: list[ScenarioFeature]
    caveats: list[str]
