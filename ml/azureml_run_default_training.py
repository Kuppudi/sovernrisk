"""Azure ML command-job entrypoint for default-onset training.

This script runs entirely on Azure ML compute:
1) Downloads global WDI archives from the World Bank API.
2) Builds the snapshot JSON expected by ml.default_training.
3) Downloads the BoC-BoE 2026 workbook.
4) Runs training and writes artifacts.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ingestion.connectors.world_bank import WorldBankClient
from ingestion.pipelines.global_world_bank import download_global_dataset
from ml.default_training import save_run, train

DEFAULT_WORKBOOK_URL = (
    "https://www.bankofcanada.ca/wp-content/uploads/2026/10/BoC-BoE-Database-2026.xlsx"
)


def build_snapshot(payload: dict, start_year: int, end_year: int) -> dict:
    observations = payload["observations"]
    digest_source = json.dumps(observations, sort_keys=True).encode("utf-8")
    dataset_version = hashlib.sha256(digest_source).hexdigest()
    return {
        "dataset_version": dataset_version,
        "manifest": {
            "source": payload["source"],
            "start_year": start_year,
            "end_year": end_year,
            "countries": payload["countries"],
            "indicators": payload["indicators"],
            "observations": observations,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    }


async def download_inputs(
    *,
    start_year: int,
    end_year: int,
    snapshot_path: Path,
    workbook_path: Path,
    workbook_url: str,
) -> None:
    async with httpx.AsyncClient(
        headers={"User-Agent": "SovereignRiskPlatform/0.1 (economic research)"},
        timeout=180,
    ) as client:
        connector = WorldBankClient(client, "https://api.worldbank.org/v2")
        payload = await download_global_dataset(connector, start_year, end_year, None)
        snapshot = build_snapshot(payload, start_year, end_year)
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=True), encoding="utf-8"
        )

        response = await client.get(workbook_url)
        response.raise_for_status()
        workbook_path.write_bytes(response.content)


def run(args: argparse.Namespace) -> None:
    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve()
    workbook_root = input_root / "global-default"

    input_root.mkdir(parents=True, exist_ok=True)
    workbook_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    snapshot_path = input_root / f"global-wdi-{args.start_year}-{args.end_year}.json"
    workbook_path = workbook_root / "BoC-BoE-Database-2026.xlsx"

    asyncio.run(
        download_inputs(
            start_year=args.start_year,
            end_year=args.end_year,
            snapshot_path=snapshot_path,
            workbook_path=workbook_path,
            workbook_url=args.workbook_url,
        )
    )

    report, model, predictions = train(
        snapshot=snapshot_path,
        workbook=workbook_path,
        train_through=args.train_through,
        validate_through=args.validate_through,
    )
    save_run(output_root, report, model, predictions)

    print(
        json.dumps(
            {
                "status": "ok",
                "selected_model": report["selected_model"],
                "threshold_from_validation": report["threshold_from_validation"],
                "snapshot_path": str(snapshot_path),
                "workbook_path": str(workbook_path),
                "output_root": str(output_root),
            },
            ensure_ascii=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=1990)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--train-through", type=int, default=2013)
    parser.add_argument("--validate-through", type=int, default=2018)
    parser.add_argument("--workbook-url", default=DEFAULT_WORKBOOK_URL)
    parser.add_argument("--input-root", type=Path, default=Path("./data/raw"))
    parser.add_argument(
        "--output-root", type=Path, default=Path("./outputs/default-onset")
    )
    run(parser.parse_args())


if __name__ == "__main__":
    main()
