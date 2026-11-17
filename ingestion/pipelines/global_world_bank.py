"""Build the global WDI panel from official per-indicator CSV archives."""

import base64
import csv
import logging
from datetime import date
from io import BytesIO, TextIOWrapper
from pathlib import Path
from zipfile import ZipFile

from ingestion.indicators import WORLD_BANK_INDICATORS
from ingestion.validation.records import ValidatedObservation, normalize_iso3

logger = logging.getLogger("sovereign.ingestion")


def csv_reader(archive: ZipFile, prefix: str):
    members = [name for name in archive.namelist() if name.startswith(prefix)]
    if len(members) != 1:
        raise ValueError(f"Expected one WDI archive member with prefix {prefix}")
    return TextIOWrapper(archive.open(members[0]), encoding="utf-8-sig", newline="")


def read_archive(content: bytes, code: str, start_year: int, end_year: int):
    with ZipFile(BytesIO(content)) as archive:
        with csv_reader(archive, "Metadata_Country_") as stream:
            countries = {}
            for row in csv.DictReader(stream):
                if not row["Region"]:
                    continue
                iso3 = normalize_iso3(row["Country Code"])
                countries[iso3] = {
                    "iso3": iso3,
                    "name": row["TableName"],
                    "region": row["Region"],
                    "income_group": row["IncomeGroup"] or "Not classified",
                }
        if not countries:
            raise ValueError("WDI archive contains no country metadata")
        with csv_reader(archive, "Metadata_Indicator_") as stream:
            metadata = next(csv.DictReader(stream))
            if metadata["INDICATOR_CODE"] != code or not metadata["SOURCE_NOTE"]:
                raise ValueError(f"Missing definition for {code}")
        indicator = {
            "code": code,
            "name": metadata["INDICATOR_NAME"],
            "definition": metadata["SOURCE_NOTE"],
            **WORLD_BANK_INDICATORS[code],
        }

        observations = []
        with csv_reader(archive, "API_") as stream:
            rows = csv.reader(stream)
            if next(rows)[:2] != ["Data Source", "World Development Indicators"]:
                raise ValueError(f"Unexpected data source for {code}")
            revision = None
            for row in rows:
                if row and row[0] == "Last Updated Date":
                    revision = date.fromisoformat(row[1])
                if row and row[0] == "Country Name":
                    reader = csv.DictReader(stream, fieldnames=row)
                    break
            else:
                raise ValueError(f"Country/year header missing for {code}")
            if revision is None:
                raise ValueError(f"WDI revision date missing for {code}")

            seen = set()
            for row in reader:
                iso3 = row["Country Code"]
                if iso3 not in countries:
                    continue
                if iso3 in seen or row["Indicator Code"] != code:
                    raise ValueError(f"Unexpected or duplicate {code} row for {iso3}")
                seen.add(iso3)
                for year in range(start_year, end_year + 1):
                    value = row.get(str(year))
                    if value is None:
                        raise ValueError(
                            f"Year {year} missing from WDI archive for {code}"
                        )
                    observation = ValidatedObservation(
                        country_iso3=iso3,
                        observation_date=date(year, 1, 1),
                        indicator_code=code,
                        value=float(value) if value else None,
                        source_revision_date=revision,
                    )
                    observations.append(observation.model_dump(mode="json"))
            if seen != countries.keys():
                raise ValueError(f"Country data missing for {code}")

    return countries, indicator, observations


async def download_global_dataset(
    connector, start_year: int, end_year: int, downloads: Path | None
):
    countries = {}
    indicators = []
    observations = []
    for code in WORLD_BANK_INDICATORS:
        url = f"{connector.base_url}/en/indicator/{code}?downloadformat=csv"
        content = (
            (downloads / f"{code}.zip").read_bytes()
            if downloads is not None
            else await connector.fetch_csv_archive(code)
        )
        catalog, indicator, records = read_archive(content, code, start_year, end_year)
        if countries and catalog.keys() != countries.keys():
            raise ValueError("WDI country coverage changed between indicator archives")
        countries = catalog
        indicators.append(indicator)
        observations.extend(records)
        connector.raw_pages.append(
            {"url": url, "zip_base64": base64.b64encode(content).decode("ascii")}
        )
        logger.info("wdi_global_series code=%s observations=%s", code, len(records))

    return {
        "source": connector.base_url,
        "countries": sorted(countries.values(), key=lambda row: row["iso3"]),
        "indicators": indicators,
        "start_year": start_year,
        "end_year": end_year,
        "observations": sorted(
            observations,
            key=lambda row: (
                row["country_iso3"],
                row["indicator_code"],
                row["observation_date"],
            ),
        ),
    }
