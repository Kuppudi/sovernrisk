"""Build annual, lag-safe features with bounded last-observation carry-forward."""

import pandas as pd

from ingestion.indicators import GLOBAL_INDICATORS

FEATURES = list(GLOBAL_INDICATORS)
MAX_FEATURE_AGE = 2


def feature_panel(snapshot: dict, through_year: int | None = None):
    observations = pd.DataFrame(snapshot["manifest"]["observations"])
    observations = observations.loc[observations["indicator_code"].isin(FEATURES)].copy()
    observations["feature_year"] = pd.to_datetime(observations["observation_date"]).dt.year
    if through_year is not None:
        observations = observations.loc[observations["feature_year"] <= through_year]
    if observations.empty:
        raise ValueError("No research features available for this date")
    wide = observations.pivot(index=["country_iso3", "feature_year"], columns="indicator_code", values="value")
    missing = set(FEATURES) - set(wide.columns)
    if missing:
        raise ValueError(f"Snapshot missing training indicators: {', '.join(sorted(missing))}")
    countries = sorted(set(wide.index.get_level_values(0)))
    first = int(wide.index.get_level_values(1).min())
    last = through_year if through_year is not None else int(wide.index.get_level_values(1).max())
    index = pd.MultiIndex.from_product([countries, range(first, last + 1)], names=wide.index.names)
    wide = wide.reindex(index=index, columns=FEATURES)
    years = pd.DataFrame({code: index.get_level_values(1) for code in FEATURES}, index=index).where(wide.notna())
    # Never backfill: later observations must not influence earlier feature years.
    return wide.groupby(level=0).ffill(limit=MAX_FEATURE_AGE), years.groupby(level=0).ffill(limit=MAX_FEATURE_AGE)
