# Project state · 2026-11-18

## Latest feature · Full-catalog research inference and risk colors

The user selected latest-data research estimates, broader country coverage and
green/yellow/red risk colors. `ml.run_training` now evaluates the historical
experiment, refits the selected learner on all eligible labeled history, and
scores the full World Bank catalog without requiring a label row for each
country being scored. Default downloads start in 1960. The same bounded two-year
carry-forward policy is applied in evaluation and inference, without future
backfill. Current annual reference year 2025 maps to outcome year 2027 under
the existing lag. Current default status remains an unverified condition.

Schema-2 latest bundles include one row per economy, input years/counts,
labeled-country coverage, and explicit nulls for insufficient data. Legacy
historical bundles remain supported. Test metrics and pre-refit artifacts remain
separate from the full-history refit artifact. The UI distinguishes latest
research from historical test results and uses fixed green/yellow/red estimate
bands, with gray for missing data. AI / RAG remains Coming soon.

Existing-data verification covered 194 of 217 economies, with 23 below the
four-feature minimum. A full-history verification fit used 2,638 eligible rows
through outcome year 2025 and 134 labeled issuers. The committed Windows result
JSON is preserved; verification outputs from the Mac are not substituted into
Git. The user must rerun training on Windows, copy the new JSON to the tracked
deployment path, commit/push and manually deploy. No Azure changes are made by
this implementation. See `DATA_SOURCES_2025.md` for researched alternatives and
why no silent IMF-to-WDI substitution is performed.

## Latest fix · Include the Windows prediction file in the deployment

The user's main push `d52c6ca` supplied valid Windows results under the singular
filename `deploy/frontend_prediction.json`. Packaging expects
`deploy/frontend_predictions.json`, so the successful release omitted the
results. The live API reported zero available predictions and MODEL_NOT_TRAINED
for the risk map, while health and the World Bank country catalog succeeded.

Rename the file to the documented plural filename without changing its bytes.
A packaging regression guard now rejects the singular spelling instead of
silently releasing without scores. The corrected local ZIP includes all 395
historical country-year predictions with metadata for 217 economies. Deployment
of the corrected main commit remains a manual user action.

## Latest delivery choice · Reviewed Windows prediction JSON in Git

GitHub Releases are not permitted in the user's environment. The user authorized
committing their Windows-generated result JSON to
`deploy/frontend_predictions.json`. The packager automatically validates and
includes that one file in the App Service ZIP. The manual deployment workflow
no longer asks for or downloads a GitHub Release asset. Both packaging workflows
use the same file discovery, with no Blob upload role required.

No prediction file is supplied from the Mac checkout. The Windows user must copy
their own `ml/artifacts/default-onset/frontend_predictions.json` to the tracked
path, commit and push it, then manually deploy the new commit. Other generated
files, raw datasets, labels, model binaries and credentials remain excluded.
`deploy/README.md` and `docs/LOCAL_TRAINING.md` contain the commands. Existing
research labels, outcome years and missing-country handling remain unchanged.
Source work does not deploy Azure or change data in an Azure storage account.

Verification: 46 focused API/file/packaging checks passed locally. The new test
confirms automatic inclusion of the committed result path, exclusion of other
deployment-folder files, and rejection of invalid JSON. Extracted-package tests
use isolated synthetic results, so CI remains independent of the user's actual
committed prediction values. Windows/Linux CI also checks this discovery path.

## Latest feature · Result delivery using App Service deployment access

The user's Windows training succeeded, but Blob publishing failed and the user
does not have Contributor access. The current alternative explicitly includes
the existing validated JSON in a locally built deployment ZIP using
`scripts.package_app_service --predictions-file`. App Service discovers the file
at `backend/app/data/frontend_predictions.json` before attempting Blob access.
An optional `PREDICTIONS_FILE` setting supports an explicit local file override.
The result loader validates/caches file contents and reports missing/invalid
configured results as unavailable.

This uses existing App Service deployment permission without a Blob role or a
storage upload. The user must deploy the locally built ZIP; a GitHub source-only
build cannot include ignored results on the laptop. Training data, model binaries
and result files remain outside Git. Ordinary packaging omits results unless
the explicit flag is supplied. Research labels and outcome years remain visible.
Other SQL paths and the broader Blob/Cosmos migration remain unchanged.

The existing manual `main_sovernriskai.yml` workflow also accepts an optional
`predictions_release_tag`. The user can attach the reviewed JSON as a GitHub
Release asset and select its tag on dispatch. The workflow downloads it from
the same repository, validates/packages it and uses the existing deployment
identity. This path needs no Azure upload/deployment role on the laptop. It
remains manual; no release asset is created and no deployment is run by this
source work. Missing/invalid assets fail before the deploy job.

Tests cover file-source precedence without cloud/SQL access, invalid/missing
files, explicit validated packaging and the actual frontend/model/map/country
APIs from an extracted release. Windows/Linux CI also checks optional packaging.
This source work performs no Azure deployment or resource changes.

Local verification passed 45 focused API/file/package checks and six ML checks.
Fresh-process tests served country/model/map results from the extracted ZIP
without Blob calls. A real research JSON containing 395 country-year predictions
was packaged successfully, while model binaries remained excluded. Standard
packaging also worked with site packages disabled, preserving the build-only
workflow's standard-library dependency boundary. The new Release-asset workflow
path remains unexecuted until the user supplies and selects a reviewed asset.

Storage account correction from the user: `sovernriskai` is the data lake and
`sovernriskaiv1` is Blob storage. Prediction uploads and `PREDICTIONS_BLOB_URL`
must use `sovernriskaiv1`. The service inventory, Copilot instructions and local
training runbook reflect this mapping. Azure ML datastore associations remain
subject to separate verification. This documentation correction changes no
Azure resources or application settings.

## Latest feature · Laptop training and hosted research results

Pulled `45814f7`, which fixes default-risk routing to `/api/data/map` instead
of the World Bank endpoint. A frontend regression test now checks the actual
request paths and probability formatting.

The user chose local Windows training with results displayed in the existing
Azure-hosted frontend. `ml.run_training` can download WDI/label inputs, train
locally and export a validated `frontend_predictions.json`. The explicit
`ml.prediction_bundle publish` command archives a version and uploads current
results into an existing private Blob container using the developer's Azure CLI
identity. No training job or SQL writes are required for this flow.

When `PREDICTIONS_BLOB_URL` is configured, model status, risk map and country
prediction reads use the Blob bundle with Azure Identity and one-minute caching.
The map/card show percentages and the historical outcome year. The card marks
results Historical research. Ineligible/missing countries remain unavailable.
Other storage paths still use SQL. Full Blob/Cosmos migration and validated
current forecasting remain incomplete. AI / RAG stays Coming soon.

`docs/LOCAL_TRAINING.md` contains native PowerShell commands, existing-resource
permissions/configuration and separate manual activation steps. Source preparation
does not deploy the app or configure/upload cloud data. The packaging tests now
use isolated database fixtures for the database-backed model status route.

Verification: 46 focused Python checks passed, the frontend route/percentage
test passed, and the TypeScript/Vite build passed. A local run against existing
real inputs exported 395 historical predictions with 217 economy records and
latest outcome year 2025. This was verified on the Mac, not the Windows laptop.
ML CI now also exercises the isolated pipeline/export tests on Windows. No
Azure upload, configuration change or deployment was performed for this work.

## Current handoff · ML starter and Azure storage direction

The user requested source delivery for Windows VS Code/Copilot and explicitly
stopped Azure publishing, then authorized merging the ML starter into main.
Both deployment workflows now require an explicit manual dispatch from main.
Source pushes run checks/packaging without Azure publishing. Earlier deployment
occurred before the user changed this instruction. No deployment is part of
the ML starter delivery or main merge.

The user has App Service, Blob Storage and Cosmos DB. Blob/Cosmos are the target
for durable data, reports and models. Current SQLAlchemy/PostgreSQL paths are
still implemented and require a storage port. Windows development uses native
Python/Node, Azure CLI and GitHub SSH. Docker and PostgreSQL Flexible Server
are outside this plan. See `AZURE_HANDOFF.md` for the service inventory,
implementation prompt and commands.

`ml/default_training.py` and `notebooks/default_training.ipynb` implement an
offline country-level default-onset experiment. It uses nine WDI features lagged
two years from outcome year, the 2026 BoC–BoE conventional-debt labels, explicit
prior-year zero debt in default, chronological train/validation/test partitions,
and event-rate/logistic/boosting comparisons. The notebook contains no saved
outputs. Input data and generated artifacts remain ignored.

The goal is a validated default-onset probability, then contextual country
report explanations. Historical-vintage validity, calibration, walk-forward
evaluation and serving integration remain incomplete. Azure ML jobs, Blob/Cosmos
adapters and live model inference are planned. Production models remain
unavailable and AI / RAG stays Coming soon. Copilot instructions now describe
this scope, the research entry points, limitations and the Azure target.

Synthetic ML checks cover label eligibility, lagged feature alignment, temporal
splits and notebook-to-artifact execution. All four passed locally on Python
3.14 with the isolated ML dependencies. The ML research workflow runs these
checks on Python 3.13 without cloud access. The run uses synthetic inputs and
does not revalidate the real-data research results or Azure runtime.

## Latest feature · API frontend and debt report research

The latest user-facing layout shows country fundamentals directly below the
map. Country comparison, report research and data explorer sections are absent
from the dashboard. AI / RAG appears as a separate Coming soon card beside the
map. Countries are selected directly on the zoomable, draggable map. The
right-hand assessment card toggles the map between default risk and 2025 GDP
growth. Default risk is the initial mode and remains explicitly unavailable
pending model validation. The map has no visible metric heading. Fundamentals
show ten compact latest-value indicators and a 2015–2025 history graph with a
ten-indicator dropdown. Wheel zoom, zoom buttons, panning, zoom reset, country
selection, mode switching and history selection were verified in the browser.
The duplicate country-indicator preview, coverage banner, extra top filters and
raw observation table were removed. Legacy comparison/report/explorer URLs return
to the dashboard. Report
processing and retrieval remain backend groundwork for a future release.

The user selected World Bank API reads for the frontend and Azure OpenAI for
report explanations. World Bank country catalogs, maps, histories, comparisons,
CSV exports and deterministic summaries now use official WDI download responses
cached in worker memory for five minutes. These frontend reads do not write
observations to disk or PostgreSQL. Saved snapshots continue to support ML.
The API path was verified live for 217 economies, ten indicators, eleven India
GDP years and the 2025 global GDP-growth map, which returned 186 numeric values.

Country report research can discover recent matching English World Bank PDFs,
process selected PDFs into country-scoped chunks, search with BM25 and open
original PDF pages. Azure OpenAI generation is implemented with server-side
configuration and validated citation identifiers. The existing research model
does not supply a validated live score. Generated explanations receive explicit
model availability and stored observation context.

Local verification processed the November 10, 2026 Kenya Economic Update into
68 pages and 228 chunks. Before the user requested the Coming soon presentation,
the research preview retrieved cited debt/refinancing passages. The report index
is preserved when a refresh fails. Embedded PDF font
decoding, missing text/OCR errors, source host validation, retries, duplicate
processing and cross-country retrieval isolation are covered.

The expanded test suite passes with 93 tests and one skip on SQLite and
PostgreSQL, and the TypeScript/Vite build passes. The additive report migration
was applied and Alembic reported no schema drift locally. Azure OpenAI has not
been called live because local endpoint, deployment and credentials are unset.
Azure report research requires the migration and server settings described in
`RAG_ARCHITECTURE.md`.

The newer Azure-generated workflow was retained and corrected to build React
and deploy the existing allowlisted application ZIP. Its automatic main-branch
deployment remains separate from local runtime verification.

## Latest feature · Global World Bank dashboard data

The local database now includes a fresh official 2015–2025 import for 217
countries/economies and ten WDI indicators, including total GDP and the existing
economic/debt series. The import contains 23,870 annual records, 19,020 reported
values and 4,850 explicit missing values. Dataset
`2708a9cc085b6d207266e631fd8f95f9d80e5053b918e5042ec86f9bf9c18074`.

The dashboard distinguishes country coverage from observation counts. Country
lists follow pagination, the explorer offers all indicators and paginated tables,
and country history/comparison defaults to 2015–2025. Total GDP is added to the
display catalog without changing the nine-feature research model schema.

Verification passed with 85 tests and one skip on both SQLite and isolated local
PostgreSQL schemas, plus the TypeScript/Vite production build. Live local API
checks verified the coverage totals and all eleven India GDP observations.
Azure deployment and import remain user-controlled and have not been performed.

Delivery uses separate feature branches, each pushed and checked before merging to `main`. The user reports the existing app is running in Azure after manual Quick Deploy, private PostgreSQL configuration, and a 396-row World Bank import. The agent has not independently verified that Azure deployment or provisioned cloud resources.

## Latest feature · World Bank extraction notebook

`notebooks/data_extract.ipynb` implements the user-approved World Bank-only data-engineering plan, with explanations before code cells. It teaches parameterization, API pagination/retries, source metadata, raw/Bronze archives, validation and missingness, cleaned/Silver observations, country-year/Gold tables, content hashes, atomic file writes, revision overlap, checkpoints, and optional PostgreSQL loading. Default runs are files-only; both database switches are false and saved execution outputs/counts are empty.

The optional load section explains what loading means, previews host/port/database without credentials, then requires a separate explicit load switch. It reuses the extracted dataset and existing atomic snapshot/audit storage. No API fetch is repeated. A failed database load leaves successful file exports available. Notebook dependencies remain outside the App Service package.

Verification: 95 tests passed in the integrated local PostgreSQL suite with the real built frontend present. The isolated notebook worktree previously passed 94 tests with one frontend-artifact skip on both SQLite and PostgreSQL; all 12 notebook tests executed. Actual-kernel World Bank extraction produced 396 rows (391 numeric, 5 null) and 66 country-years while a deliberately invalid database URL remained unused. An actual three-year incremental refresh fetched 108 rows and retained the same 396-row dataset hash. Repeated optional loads produced 24 synthetic observations, one snapshot, and two audits in a disposable PostgreSQL schema, with no additional API fetch.

IMF (`2e0d1d7`) and ADB (`bcf49ee`) were separately pushed, checked by GitHub Backend/Frontend/App Service packaging workflows, and merged to main before notebook delivery. User-controlled Azure Quick Deploy and data imports are still required for these changes. Azure ML notebook execution has not been performed. ML model training and RAG remain separate future features.

## Previous feature · ADB ingestion

Branch `feature/adb-ingestion` adds total international reserves, long-term principal repayments, and long-term interest payments through ADB KIDB SDMX CSV. USD scales are normalized to million US$, legacy economy codes map to ISO3, and unsupported/subnational codes fail validation. Original sources, reference periods, footnotes, and statuses remain in the manifest. Missing catalog descriptions are disclosed; gaps are not filled. Requests stay below the documented 20/minute limit.

Local evidence: 83 tests passed on PostgreSQL 17.11 and the frontend production build passed. Official ADB import for India/Japan, 2015–2025, added 44 numeric observations: 22 reserve values and 11 each of the debt cash-flow series (India only). Snapshot `b31175f719c7e0b37d09b15316e5b0b61eeab63c570132cd8cf302e7b2f05c3b`. Local stored observations now total 704, including WDI and IMF. Azure needs the new package and CLI commands; no schema change or added service is required.

## Previous feature · IMF ingestion

Branch `feature/imf-ingestion` adds four fiscal indicators from IMF DataMapper v2: WEO debt and overall balance, plus Fiscal Monitor primary balance and revenue. All use percent of GDP. IMF codes and original metadata remain separate from WDI. Unknown cutoffs, projection years, changed datasets/units, invalid values, and empty country scopes fail; earlier estimates and missing history remain explicitly disclosed. Country registration is reused from World Bank.

Shared `storage.py` and `runs.py` retain atomic writes, raw archives, immutable revisions, and import audits. The frontend uses actual provider attribution and units in the indicator map, country preview, comparison, and reports. Existing World Bank CLI commands remain compatible. No schema migration, new paid resource, training, or RAG is added.

Local evidence: 68 tests passed on PostgreSQL 17.11; frontend TypeScript/Vite production build passed. A live official IMF import added 264 observations for the existing six countries over 2015–2025, snapshot `b31850e3158a57314bb73478ccea6802920f481e2069ee8abe36cdf167a7da3e`. New data is local only; Azure still needs the new package and import command. See `DATA_IMPORTS.md`.

## Latest feature · single App Service

The conversion branch is `feature/single-app-service`, based on refreshed main `5d7f92c` (including the user's generated Static Web Apps workflow). React's compiled frontend and FastAPI now share one Python server and one URL. API requests and CSV exports are relative; no separate frontend/API origin is needed.

`backend/app/frontend.py` contains the small frontend-serving function. Known React URLs return index.html so direct links and refreshes work. `/api`, `/docs`, assets, and map files retain their own routes; missing API routes/assets stay 404s. Backend development still runs without a built frontend, while `startup.sh` refuses an incomplete production deployment.

`scripts/package_app_service.py` creates `dist/app-service.zip` with app code, migrations, requirements, the startup script, and built frontend. It excludes local data, credentials, node_modules, caches, and tests. The generated Static Web Apps workflow is removed; the new App Service workflow builds/packages on pushes and deploys only on an explicit manual run from main. No Azure resource, secret, or existing Static Web App is modified by this code change.

Local validation: 56 tests passed on SQLite and PostgreSQL 17.11, including shared hosting, direct links, missing assets/API routes, packaging exclusions, missing build rejection, and a fresh-process smoke test from an extracted real deployment ZIP. Production TypeScript/Vite build and shell syntax check passed; Alembic found no schema drift. The browser verified the whole app on Python port 8000, indicator history, country/report refreshes, and same-origin CSV links, with no console errors or warnings. No Vite server was running. Azure deployment remains unverified until the user configures an existing App Service and manually deploys. See `infrastructure/azure/README.md` for exact settings and steps.

The user requested ML training in `.ipynb` notebooks as the next separate feature, followed by RAG. No notebook or new ML training code is claimed by this hosting conversion; models remain explicitly unavailable.

## Current interface

App name: **SovereignRisk AI**. Main headline: **Sovereign Credit Risk**. The first page defaults to ML risk assessment, with a country selector, gray risk map, and a concise Not trained/Unavailable score panel. Promotional and instructional paragraphs have been removed. The Indicators view separately shows official economic values; these never populate risk scores. On phones, the ML panel appears before the map.

Intended use is sovereign lending/repayment-risk analysis for development-finance institutions, other lenders, and insurers. Repayment/default risk and rating-downgrade probability are separate targets. No trained model, repayment probability, credit score, or fabricated prediction is available.

## Feature delivery

1. `feature/ml-risk-homepage`: frontend, minimal ML homepage, indicator view, country selection, reports/data pages, frontend CI. Commit `dfc484a`; GitHub frontend build passed and the branch was merged/pushed to main first.
2. `feature/backend-api`: FastAPI, PostgreSQL schema/migrations, environment/Compose configuration, API services, backend CI. Commit `2bee0e7`; frontend/backend GitHub jobs and PostgreSQL migration cycle passed before main merge.
3. `feature/world-bank-ingestion`: official WDI connector, validation, source archives, snapshots, CLI, and data/API integration tests. Commit `878f415`; local full suite passed on SQLite/PostgreSQL. Both GitHub jobs also passed, including the PostgreSQL migration cycle, before main merge.
4. Project documentation, model limitations, and Azure planning notes are delivered separately after the functional features. These notes do not provision resources or implement model training.

## Code structure

`docs/CODE_GUIDE.md` explains the reading order. The ingestion command uses a short orchestrator, separate download/validation and storage modules, and explicit run auditing. Reports and CSV formatting are separate from HTTP handlers. The existing archived dataset identifier was verified unchanged by the readability refactor.

The world map bundles public-domain Natural Earth v5.1.2 outlines locally. Economic coverage remains six imported countries. `GET /api/data/map` returns latest-vintage observations for the exact selected year, with no older-value fallback.

Validation: 35 tests passed on SQLite and PostgreSQL 17.11; strict TypeScript/production build passed; schema check found no drift. Browser checks verified default unavailable risk state, country selection, indicator/risk separation, year changes, keyboard interaction, phone layout, and no page-level horizontal overflow. The compiled frontend had no browser warnings/errors. Current screenshot: ignored `data/ml-risk-homepage.jpg`. Verification services are stopped after checks; source and imported data remain available for restart.

## Milestone 1 · Implemented

React/TypeScript/Vite/Tailwind frontend; FastAPI/Pydantic API; SQLAlchemy models; Alembic migration; PostgreSQL Compose; environment examples; API connectivity and CORS; structured JSON request logs; consistent errors; persistent Copilot context. Actual PostgreSQL initialization, migration upgrade, and schema drift check passed using an isolated project-local PostgreSQL runtime because Docker was not installed. The Compose container itself has not been run.

## Milestone 2 · Implemented

World Bank WDI connector, six requested mappings, pagination and retry handling, finite numeric validation, explicit nulls, country/indicator metadata, atomic persistence, failed-run audits, raw JSON archives, content-addressed snapshots, incremental/overlapping refreshes, latest-vintage selection, country/indicator/year retrieval, freshness, and manual CLI. Publication dates stay unknown; provider response revision dates are preserved separately.

Live import succeeded for BRA, DEU, IND, JPN, USA, ZAF, 2015–2025: **396 observation records: 391 reported values and 5 explicit nulls**. Dataset snapshot: `af2ed7c32d049e5745d1e13a152b1cf30e6b38184245c7def8acf31bda67910f`. Original responses and database are ignored local artifacts. One temporary source failure was recovered through the connector retry path.

## Milestones 3–4 · Initial implementation, incomplete

The map home page, country selection, exact-year economic values, annual time-series charts, freshness, country analysis, comparison, explorer, CSV exports, and deterministic print-friendly country reports are implemented. Latest non-null report summaries disclose differing years and later gaps. Browser print/save-to-PDF is available; server-side PDF and report historical chart sections remain incomplete. Governance, debt, reserves, fiscal balance, and corruption datasets are explicitly absent. Broader coverage, automated UI regression/accessibility checks, and production UI refinements remain.

## Milestone 5 · Not started

Only reserved schema/directories and model card exist. No authorized ratings, target, training, calibration, backtesting, SHAP, or inference artifacts. Risk/downgrade API requests return explicit HTTP 503 `MODEL_NOT_TRAINED`; model status returns HTTP 200 unavailable. No arbitrary scores or synthetic production data.

## Milestone 6 · Single-service packaging implemented; deployment reported by user

React/FastAPI shared hosting, startup script, a source ZIP packager, deployment documentation, and a manual OIDC deployment workflow exist. The user reports a successful manual Quick Deploy, private database connection, and World Bank import. New data features require another manual deployment. Agent verification is local/CI only. Blob storage, database managed-identity authentication, production access control, and monitoring refinements remain future work. The agent has created no paid resources.

## Verification

- Foundation suite (Nov 3): **35 passed on SQLite and PostgreSQL 17.11**. The Nov 10 App Service suite expands this to **56 passing tests** on both databases, adding frontend routing and deployment-package verification.
- Strict TypeScript and final production frontend build: passed without bundle-size warnings after separating framework/chart chunks.
- PostgreSQL migration upgrade and final `alembic check`: passed; no drift. SQLite migration upgrade/downgrade/schema equivalence test passed. GitHub CI also passed a PostgreSQL downgrade/upgrade cycle on the backend feature branch.
- Python dependency consistency check: passed.
- Live frontend/proxy/API checks: HTTP 200 frontend/health/report; real-data freshness showed 6 countries and 396 records; prediction returned the expected HTTP 503.
- Browser checks passed for overview, country search, India analysis, India/USA comparison chart and tables, explorer country/year filters, CSV download, deterministic India report, print/save-PDF control, and explicit missing-data/model limitations. Print-to-PDF output itself was not generated or visually verified.
- Compiled production frontend preview: loaded and connected to the API with no browser console errors. Mobile/default and desktop layouts were inspected; checked viewport/content widths matched, with no page-level horizontal overflow. Comprehensive accessibility/device regression testing remains incomplete.
- A local preview screenshot is saved at ignored `data/dashboard-desktop.jpg`. Verification frontend/API/database services are stopped after checks; source, database, and raw downloads are retained for restart.
- Remote GitHub CI: frontend, backend, and ingestion feature checks verified passing before their main merges. Both workflows also run on main pushes.

## Known limitations and next steps

Complete milestone 3 QA/coverage first, then expand milestone 4 reports. Data availability and annual vintage limitations must remain visible. Ingestion supports a single writer; concurrent snapshot insert coordination and abandoned-run recovery are deferred. Current metadata can evolve; original metadata is recoverable in the raw manifest. Archive files must be backed up with database rows. No historical knowledge-at-time inference can be made from newly downloaded WDI history alone. Production authentication, rate limits, and deployment hardening are not yet implemented. Current test dependencies emit an upstream Starlette/httpx deprecation warning without test failures.

Use README for Docker setup or `docs/LOCAL_VERIFICATION.md` to reuse this session's downloaded PostgreSQL runtime. Do not confuse local build/runtime verification with Azure deployment.
