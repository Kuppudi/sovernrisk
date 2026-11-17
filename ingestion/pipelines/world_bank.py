"""Download World Bank observations and save an audited, immutable dataset."""

import asyncio
from datetime import date

from ingestion.pipelines.global_world_bank import download_global_dataset
from ingestion.pipelines.runs import finish_run, record_failure, start_run
from ingestion.pipelines.world_bank_data import download_dataset
from ingestion.validation.records import normalize_iso3


async def ingest_world_bank(
    db, connector, countries, start_year, end_year, raw_dir, *, downloads=None
):
    requested = (
        None
        if countries is None
        else sorted({normalize_iso3(code) for code in countries})
    )
    if requested is not None and not 1 <= len(requested) <= 60:
        raise ValueError("Request between 1 and 60 countries per run")
    if not 1960 <= start_year <= end_year <= date.today().year:
        raise ValueError("Invalid observation year range")
    run = start_run(
        db,
        "World Bank WDI",
        connector.base_url,
        "World Bank datasets generally use CC BY 4.0; verify dataset-specific terms and third-party restrictions before redistribution.",
    )
    run_id = run.id
    try:
        if requested is None:
            dataset = await download_global_dataset(
                connector, start_year, end_year, downloads
            )
        else:
            dataset = await download_dataset(connector, requested, start_year, end_year)
        return finish_run(db, run, dataset, connector.raw_pages, raw_dir)
    except (Exception, asyncio.CancelledError) as error:
        record_failure(db, run_id, error)
        raise
