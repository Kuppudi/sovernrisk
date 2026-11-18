# Sovereign default-onset ML starter

For the current laptop-to-hosted-frontend workflow, follow
[local training and result delivery](../docs/LOCAL_TRAINING.md). `ml.run_training`
downloads inputs and trains on the laptop. Copy the reviewed Windows JSON to
`deploy/frontend_predictions.json`, commit and push it, then manually deploy
the new commit. Azure ML compute and Blob upload access are unnecessary for
that path. Other generated files remain excluded from Git.

The default-onset experiment uses a global World Bank WDI snapshot and the
2026 BoC–BoE sovereign default workbook. It predicts whether conventional
debt in default becomes positive in the following calendar year among
issuers with explicit zero debt in default the prior year.

After the global import in [data imports](../docs/DATA_IMPORTS.md), find the
archive at `data/raw/<ingestion-run-id>.json`. Download the 2026 workbook from
the [Bank of Canada release](https://www.bankofcanada.ca/2026/10/staff-analytical-paper-2026-48/).
Install the ML dependencies with `python -m pip install -e '.[ml]'`.

```sh
python -m ml.default_training \
  --snapshot data/raw/RUN_ID.json \
  --default-workbook data/raw/global-default/BoC-BoE-Database-2026.xlsx \
  --output ml/artifacts/default-onset
```

Replace `RUN_ID` with the ID printed by the import command.

The same pipeline runs from [the training notebook](../notebooks/default_training.ipynb).
The experiment uses revised historical WDI values and an assumed reporting lag.
The metrics and test predictions are retrospective. The API keeps both
production models unavailable pending historical-vintage validation.

## Windows VS Code

Use a snapshot covering 1990–2025 to reproduce the default split dates. A
2015–2025 dashboard snapshot alone cannot supply the training partition.
The current importer still uses SQL persistence. Follow
[the Azure handoff](../docs/AZURE_HANDOFF.md) to port snapshots to Blob;
the training module itself reads files and needs no database or Docker.
Supply an existing exported snapshot and the official workbook locally.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ml]"
.\.venv\Scripts\python.exe -m pytest -q ml/tests
.\.venv\Scripts\python.exe -m ml.default_training `
  --snapshot "C:\vega-inputs\wdi-snapshot.json" `
  --default-workbook "C:\vega-inputs\BoC-BoE-Database-2026.xlsx" `
  --output "ml/artifacts/default-onset"
```

To run the notebook, select a kernel with the same ML dependencies and set
`WDI_SNAPSHOT`, `DEFAULT_WORKBOOK` and optionally `DEFAULT_MODEL_OUTPUT` to your
paths. Install a Jupyter kernel in that development environment if needed.
Input downloads and generated artifacts stay outside Git.

## What we are trying to achieve

Build an evaluated country-level default-onset probability with a precise
forecast horizon and data coverage. The starter compares an event-rate baseline,
logistic regression and histogram gradient boosting. It selects a model and
threshold using validation years and reports historical test performance.

Before live scores, verify label coverage/semantics, historical feature
availability, calibration, walk-forward performance, missingness and subgroup
coverage. An assumed two-year feature lag does not solve revised-history bias.
The starter has no production inference integration or Azure ML job definition.

The planned Azure flow is versioned datasets in Blob → Azure ML training and
evaluation → reviewed model artifacts in Blob → App Service inference, with
prediction/model metadata in Cosmos DB. A later Azure OpenAI RAG branch will
retrieve country PDF evidence and explain it alongside the model output with
page citations. The public AI / RAG card stays Coming soon.
