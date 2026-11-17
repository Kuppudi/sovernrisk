"""Read official WDI download API responses into a five-minute memory cache."""

import asyncio
import hashlib
import threading
import time
from datetime import UTC, datetime
from functools import lru_cache
from zipfile import BadZipFile

import httpx
from fastapi import HTTPException

from backend.app.core.config import get_settings
from backend.app.schemas.api import CountryOut, IndicatorOut, ObservationOut
from ingestion.connectors.http import SourceError
from ingestion.connectors.world_bank import WorldBankClient
from ingestion.indicators import WORLD_BANK_INDICATORS
from ingestion.pipelines.global_world_bank import read_archive

CACHE_SECONDS = 300
START_YEAR = 2015
END_YEAR = 2025
_panel_lock = threading.Lock()


def cache_bucket() -> int:
    return int(time.monotonic() // CACHE_SECONDS)


@lru_cache(maxsize=2)
def _download_panel(bucket: int):
    async def download():
        semaphore = asyncio.Semaphore(3)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            connector = WorldBankClient(client, get_settings().world_bank_base_url)

            async def series(code):
                async with semaphore:
                    return code, await connector.fetch_csv_archive(code)

            return await asyncio.gather(
                *(series(code) for code in WORLD_BANK_INDICATORS)
            )

    try:
        archives = asyncio.run(download())
        countries = {}
        definitions = []
        observations = []
        retrieved = datetime.now(UTC)
        for code, content in archives:
            places, definition, records = read_archive(
                content, code, START_YEAR, END_YEAR
            )
            if countries and countries.keys() != places.keys():
                raise ValueError("Country coverage changed between responses")
            countries = places
            definitions.append(IndicatorOut(**definition, source_id=0))
            version = hashlib.sha256(content).hexdigest()
            for record in records:
                observations.append(
                    ObservationOut(
                        **record,
                        indicator_name=definition["name"],
                        unit=definition["unit"],
                        publication_date=None,
                        retrieved_at=retrieved,
                        dataset_version=version,
                        source="World Bank WDI",
                        source_url=f"https://data.worldbank.org/indicator/{code}",
                    )
                )
        places = sorted(
            [CountryOut(**row) for row in countries.values()], key=lambda row: row.name
        )
        definitions.sort(key=lambda row: row.code)
        observations.sort(
            key=lambda row: (row.country_iso3, row.indicator_code, row.observation_date)
        )
        return places, definitions, observations
    except (SourceError, ValueError, KeyError, TypeError, BadZipFile):
        raise HTTPException(
            502,
            {
                "code": "WORLD_BANK_UNAVAILABLE",
                "message": "The World Bank API could not return the requested data. Try again.",
            },
        ) from None


def panel(bucket: int):
    # Share an initial fetch between concurrent requests in this worker process.
    with _panel_lock:
        return _download_panel(bucket)


def catalog(bucket: int) -> tuple[list[CountryOut], list[IndicatorOut]]:
    places, definitions, _ = panel(bucket)
    return places, definitions


def country(code: str) -> CountryOut:
    places, _ = catalog(cache_bucket())
    for place in places:
        if place.iso3 == code:
            return place
    raise HTTPException(404, "This country/economy is not in the World Bank catalog.")


def observations(
    countries: tuple[str, ...],
    codes: tuple[str, ...],
    start: int,
    end: int,
    bucket: int,
) -> list[ObservationOut]:
    if not START_YEAR <= start <= end <= END_YEAR:
        raise HTTPException(422, "Choose years from 2015 through 2025.")
    places, definitions, rows = panel(bucket)
    if set(countries) - {place.iso3 for place in places}:
        raise HTTPException(404, "An unknown World Bank country/economy was selected.")
    if set(codes) - {item.code for item in definitions}:
        raise HTTPException(
            422, "An indicator is outside the configured World Bank catalog."
        )
    country_codes = set(countries)
    indicator_codes = set(codes)
    return [
        row
        for row in rows
        if row.country_iso3 in country_codes
        and row.indicator_code in indicator_codes
        and start <= row.observation_date.year <= end
    ]
