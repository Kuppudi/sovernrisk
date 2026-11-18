"""Portable research results shared by the local trainer and the serving API."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.api import CountryOut, PredictionOut


class PredictionBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    status: Literal["historical_research"] = "historical_research"
    model_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    generated_at: AwareDatetime
    target: Literal["default_onset"] = "default_onset"
    limitation: str = Field(min_length=1)
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
            if not row.research_only or row.risk_score is None:
                raise ValueError("Bundle requires research probabilities")
            if row.outcome_year is None or row.feature_year != row.outcome_year - 2:
                raise ValueError("Outcome and lagged feature years are required")
            if row.as_of_date.year != row.outcome_year - 1:
                raise ValueError("Invalid historical as-of year")
            if row.model_version != self.model_version or row.data_snapshot_id != self.dataset_version:
                raise ValueError("Prediction provenance does not match bundle")
        return self
