"""Portable research results shared by the local trainer and the serving API."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.api import CountryOut, PredictionOut
from ingestion.indicators import GLOBAL_INDICATORS


class PredictionBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1, 2] = 1
    status: Literal["historical_research", "latest_research"] = "historical_research"
    model_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    generated_at: AwareDatetime
    target: Literal["default_onset"] = "default_onset"
    limitation: str = Field(min_length=1)
    feature_codes: list[str] = Field(default_factory=list)
    max_feature_age_years: int = Field(default=0, ge=0, le=2)
    countries: list[CountryOut] = Field(min_length=1, max_length=300)
    predictions: list[PredictionOut] = Field(min_length=1, max_length=30000)

    @model_validator(mode="after")
    def consistent_research_results(self):
        codes = {country.iso3 for country in self.countries}
        if len(codes) != len(self.countries):
            raise ValueError("Duplicate countries in prediction bundle")
        if any(len(code) != 3 or not code.isascii() or not code.isalpha() or code != code.upper() for code in codes):
            raise ValueError("Countries must use uppercase ISO3 codes")
        keys = set()
        for row in self.predictions:
            key = (row.country_iso3, row.outcome_year)
            if key in keys:
                raise ValueError("Duplicate country/outcome year")
            keys.add(key)
            if row.country_iso3 not in codes:
                raise ValueError("Prediction country absent from country catalog")
            if not row.research_only:
                raise ValueError("Bundle requires research results")
            if self.status == "historical_research" and row.risk_score is None:
                raise ValueError("Historical bundle requires probabilities")
            if row.outcome_year is None or row.feature_year != row.outcome_year - 2:
                raise ValueError("Outcome and lagged feature years are required")
            if row.as_of_date.year != row.outcome_year - 1:
                raise ValueError("Invalid historical as-of year")
            if row.model_version != self.model_version or row.data_snapshot_id != self.dataset_version:
                raise ValueError("Prediction provenance does not match bundle")
            if row.research_kind != self.status:
                raise ValueError("Prediction kind does not match bundle")
            if self.status == "latest_research":
                if row.in_training_coverage is None:
                    raise ValueError("Latest estimates require training-country coverage metadata")
                if self.schema_version != 2 or self.feature_codes != list(GLOBAL_INDICATORS):
                    raise ValueError("Latest estimates require schema 2 and nine feature codes")
                if row.observed_feature_count != len(row.feature_years):
                    raise ValueError("Feature coverage count mismatch")
                if not set(row.feature_years) <= set(self.feature_codes):
                    raise ValueError("Unknown research feature")
                if any(year > row.feature_year or year < row.feature_year - self.max_feature_age_years for year in row.feature_years.values()):
                    raise ValueError("Features are future dated or stale")
                enough = row.observed_feature_count >= 4
                if enough != (row.risk_score is not None) or enough != (row.availability == "available"):
                    raise ValueError("Score availability must match input coverage")
        if self.status == "latest_research":
            if len({row.outcome_year for row in self.predictions}) != 1 or len(self.predictions) != len(codes):
                raise ValueError("Latest bundle must cover every catalog country for one outcome year")
        return self
