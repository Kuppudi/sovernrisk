# VEGA · country economic data and sovereign default-risk research

Read this file, `docs/PROJECT_STATE.md`, `docs/DECISIONS.md`,
`docs/AZURE_HANDOFF.md`, `ml/README.md` and `docs/MODEL_CARD.md`
before changing the project. The latest decisions below supersede older
PostgreSQL, Docker, dashboard-tab and automatic-merge instructions.

## Product and current implementation

- Goal: help users understand a country's economic fundamentals and, after
  validation, its sovereign default risk. Later, explain a real model result
  alongside relevant official country debt-report passages with page citations.
- React/TypeScript/Vite and FastAPI share one existing Azure App Service.
  World Bank frontend data comes from `/api/live/world-bank/...`, with a short
  server memory cache, ten economic/debt indicators and 2015–2025 coverage.
  Store versioned datasets separately for reproducible training.
- Keep the dashboard simple. Select countries on the zoomable, draggable map.
  The right-hand card toggles default risk and GDP growth. Show compact country
  fundamentals inline and retain the history graph's indicator dropdown.
  Keep AI / RAG as a Coming soon card. Country dropdowns, comparison, report
  browsing, data explorer, provenance panels and extra top indicator cards are
  absent from the public UI.
- Production risk models remain unavailable. GDP growth is an economic
  measurement. A future default probability needs a defined event, horizon,
  model version and as-of date. Never fabricate ratings, scores or explanations.

## ML beginnings and intended outcome

- Start with `notebooks/default_training.ipynb` and `ml/default_training.py`.
  The notebook calls the shared offline training pipeline. It has no saved
  outputs. Install optional dependencies with `python -m pip install -e '.[ml]'`.
  See `ml/README.md` for Windows commands and required input files.
- The current research target is **sovereign default onset** in outcome year Y:
  conventional debt in default becomes positive after an explicit zero stock
  in Y-1, using the 2026 BoC–BoE workbook. Ongoing defaults, unknown prior status
  and negative stocks are excluded. This target has country-level scope.
  Loan repayment and rating downgrades require their own outcomes and labels.
- Inputs are immutable WDI snapshots and the official label workbook. The
  nine-feature schema is `ingestion.indicators.GLOBAL_INDICATORS`. Total GDP is
  a tenth display indicator outside that research schema. Retain nulls and
  require at least four observed research features per eligible row.
- The starter uses Y-2 annual features for an end-of-Y-1 forecast of Y. This is
  an assumed publication lag. Revised WDI history does not establish what was
  known at the historical prediction date. Resolve that limitation before
  interpreting backtest probabilities as live lending forecasts.
- Train through 2013, select model and classification threshold on 2014–2018,
  and evaluate on 2019–2025. Training needs longer history than the frontend's
  2015–2025 display window. Keep model/threshold selection outside the test set.
- Existing candidates are an event-rate baseline, median-imputed/scaled logistic
  regression and histogram gradient boosting. Compare PR performance, ROC-AUC,
  Brier score and confusion matrices. Preserve saved-run provenance and report
  rare-event coverage and false positives. Local historical test predictions
  and research artifacts are excluded from Git.
- Next ML work: validate label semantics/coverage, feature units and historical
  availability; add walk-forward evaluation and calibration/reliability checks;
  examine country/period coverage and missingness; version schemas, dependencies,
  data hashes and artifacts. Repeated experiments must not turn the historical
  test period into another tuning set. Production approval is a separate step.
- Intended delivery: Azure ML runs offline training/evaluation with versioned
  Blob datasets on Azure-managed compute. Export trusted reviewed artifacts to
  Blob, record model references and versioned country predictions in Cosmos DB,
  and let App Service load an appropriate artifact for lightweight inference.
  Do not train during API requests. No production scorer or AML job is wired yet.
- RAG is a later, separate evidence branch: official PDFs in Blob, page chunks
  and metadata in Cosmos DB, country-scoped retrieval, then Azure OpenAI using
  passages plus the actual model result/availability and dated structured data.
  Report evidence provides context. Claimed model drivers need validated
  attributions from the model itself. Keep the public card Coming soon.

## Azure and Windows direction

- The user has an App Service, Blob Storage and Cosmos DB already. Discover
  their actual names, endpoints, Cosmos API and identities using Azure CLI.
  Target Blob for PDFs/datasets/models and Cosmos for metadata/chunks/predictions.
  Read `docs/AZURE_HANDOFF.md` for the implementation plan.
- SQLAlchemy/PostgreSQL, local PDF archives and SQL-backed health/report paths
  still exist in the code. The Blob/Cosmos migration is planned, not implemented.
  Changing connection strings alone does not perform that migration. Preserve
  latest-vintage, explicit-null, retry and failed-refresh behavior while porting.
- Develop in Windows VS Code with PowerShell, native Python/Node, the existing
  Azure CLI identity and GitHub SSH. Use Azure services for the cloud runtime.
  Do not introduce Docker, database emulators or PostgreSQL Flexible Server.
  Azure ML and Azure OpenAI are planned services; discover existing resources
  before proposing additions. OCR is optional if scanned PDFs require it.
- Use Azure Identity locally and managed identity in Azure. Scope Blob/Cosmos
  data-plane permissions to each caller. Keep credentials server-side and out
  of Git, notebooks, logs and frontend bundles. Reuse SDK clients. Blob/Cosmos
  writes need explicit version completion and recovery, since they span stores.

## Working and delivery rules

- Preserve the modular monorepo, readable functions and existing user work.
  Run Python modules from the repository root. Align API schemas and frontend
  contracts. Preserve dates, provider revisions, source URLs, hashes and nulls.
- Create a feature branch, verify locally, push that branch and inspect CI.
  Merge main only when the user requests it. A main merge does not authorize
  Azure publishing. Both App Service deployment workflows require an explicit
  manual dispatch from main. Keep push/PR workflows limited to checks and
  packaging. Never dispatch deployment as part of source delivery.
- Do not provision/scale Azure resources or start cloud ML jobs without an
  explicit instruction. Source delivery does not authorize those actions.
  Keep ML dependencies and artifacts outside the App Service package.
- Run meaningful tests for the changed behavior. ML checks run with
  `python -m pytest -q ml/tests` after installing `.[dev,ml]`. Synthetic test
  inputs must be isolated. Existing backend CI still uses PostgreSQL until the
  storage migration; report exactly which runtime was verified.
- Update PROJECT_STATE, DECISIONS and the model card when scope/status changes.
  Distinguish completed research, planned services and validated live behavior.
