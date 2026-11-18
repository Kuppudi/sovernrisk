"""Train on this computer and export frontend results without a database or AML job."""

import argparse
import asyncio
from pathlib import Path

from ml.azureml_run_default_training import DEFAULT_WORKBOOK_URL, download_inputs
from ml.default_training import save_run, train
from ml.prediction_bundle import export_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-inputs", action="store_true")
    parser.add_argument("--snapshot", type=Path, default=Path("data/raw/global-wdi-1990-2025.json"))
    parser.add_argument("--default-workbook", type=Path, default=Path("data/raw/global-default/BoC-BoE-Database-2026.xlsx"))
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/default-onset"))
    args = parser.parse_args()
    if args.download_inputs:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.default_workbook.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(download_inputs(
            start_year=1990, end_year=2025, snapshot_path=args.snapshot,
            workbook_path=args.default_workbook, workbook_url=DEFAULT_WORKBOOK_URL,
        ))
    for path in (args.snapshot, args.default_workbook):
        if not path.is_file():
            parser.error(f"Input missing: {path}. Supply files or use --download-inputs.")
    report, model, predictions = train(args.snapshot, args.default_workbook)
    save_run(args.output, report, model, predictions)
    print(f"Selected model: {report['selected_model']}")
    print(f"Frontend research results: {export_bundle(args.snapshot, args.output)}")
    print("Training completed locally. No results uploaded or Azure ML job submitted.")


if __name__ == "__main__":
    main()
