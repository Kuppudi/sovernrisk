"""Train on this computer and export frontend results without a database or AML job."""

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from ml.azureml_run_default_training import DEFAULT_WORKBOOK_URL, download_inputs
from ml.default_training import save_run, train
from ml.prediction_bundle import export_bundle
from ml.latest_estimates import latest_estimates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-inputs", action="store_true")
    parser.add_argument("--start-year", type=int, default=1960)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--default-workbook", type=Path, default=Path("data/raw/global-default/BoC-BoE-Database-2026.xlsx"))
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/default-onset"))
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--historical-results", action="store_true", help="Export held-out historical rows instead of latest-data estimates")
    args = parser.parse_args()
    feature_year = args.as_of_date.year - 1
    if not 1960 <= args.start_year <= feature_year:
        parser.error("Start year must be between 1960 and the feature reference year")
    if args.snapshot is None:
        args.snapshot = Path(f"data/raw/global-wdi-{args.start_year}-{feature_year}.json")
    if args.download_inputs:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.default_workbook.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(download_inputs(
            start_year=args.start_year, end_year=feature_year, snapshot_path=args.snapshot,
            workbook_path=args.default_workbook, workbook_url=DEFAULT_WORKBOOK_URL,
        ))
    for path in (args.snapshot, args.default_workbook):
        if not path.is_file():
            parser.error(f"Input missing: {path}. Supply files or use --download-inputs.")
    report, model, predictions = train(args.snapshot, args.default_workbook)
    save_run(args.output, report, model, predictions)
    print(f"Selected model: {report['selected_model']}")
    if args.historical_results:
        result = export_bundle(args.snapshot, args.output)
    else:
        result = latest_estimates(args.snapshot, args.default_workbook, report, model, args.output, args.as_of_date)
    print(f"Frontend research results: {result}")
    bundle = json.loads(result.read_text(encoding="utf-8"))
    if bundle["status"] == "latest_research":
        scored = sum(row["risk_score"] is not None for row in bundle["predictions"])
        print(f"Latest-data research estimates: {scored}/{len(bundle['countries'])} economies; forecast year {bundle['predictions'][0]['outcome_year']}.")
    print("Training completed locally. No results uploaded or Azure ML job submitted.")


if __name__ == "__main__":
    main()
