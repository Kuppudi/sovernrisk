# SovereignRisk AI — Azure Service Guide

This README records the Azure services known to belong to SovereignRisk AI and what
role each service currently has. It is intended as an operational inventory, not
as authorization to change resources or deploy code.

## Current subscription and hosting

- **Subscription:** `cb5580632a-iotcsazure-az`
- **Subscription ID:** `97c7b242-6f62-4912-b4e3-373a6e52ad78`
- **Tenant ID:** `de08c407-19b9-427d-9fe8-edf254300ca7`
- **Resource group:** `wbg-poc-rg`
- **Primary region:** East US 2 for the App Service and Flexible Server; some ML,
  storage, Cosmos DB and supporting resources are in East US.

## Service inventory

| Azure service | Resource name | Purpose and current status |
| --- | --- | --- |
| App Service | `sovernriskAI` | Hosts the React frontend and FastAPI API together on Linux. Running; public host is `sovernriskai-c8dbcqe6edapeuae.eastus2-01.azurewebsites.net`. |
| App Service plan | `ASP-wbgpocrg-afce` | Compute plan for `sovernriskAI`. |
| PostgreSQL Flexible Server | `sovernriskai-server` | Primary relational database currently used by the application. PostgreSQL 14, `Standard_D2s_v3`, Ready, private network access disabled from public access. |
| Storage account / ADLS Gen2 | `sovernriskai` | User-confirmed data lake for raw, versioned and curated datasets. |
| Storage account / Blob | `sovernriskaiv1` | User-confirmed Blob storage for prediction result JSON, model artifacts, report files and other binary outputs. |
| Cosmos DB for NoSQL | `wbgpoc-cosmosdb` | GlobalDocumentDB/Core SQL account. Reserved for application metadata and future RAG/model data. No Cosmos integration is currently confirmed in application code or App Service settings. |
| Azure Machine Learning workspace | `sovernriskAI-diviml` | Workspace used for ML development and hosted ML compute. The workspace is in East US. |
| Application Insights | `sovernriskAI` | Application telemetry and diagnostics connected to the App Service. |
| Azure Key Vault | `wbgpoc-kv` and other vault resources | Secret and key storage. App credentials must remain out of source and logs. |
| Azure Data Factory | `wbgpoc-df` | Supporting data orchestration resource. It is not confirmed to be part of the current application runtime. |
| GitHub OIDC identity | `sovernrisk-gh-oidc` | User-assigned identity used for GitHub-to-Azure deployment identity. |
| Virtual network / private endpoints | `wbgpoc-vnet`, `vnet-cfouxtit` and private endpoint resources | Private networking infrastructure for Azure data and platform services. |

## Flexible Server: how the app uses it now

`sovernriskai-server` is the application's current SQLAlchemy/PostgreSQL database.
The App Service configuration includes `DATABASE_URL`; the application creates a
SQLAlchemy engine from that setting and uses pooled sessions with pre-ping checks.

The server stores the following application data:

- Countries and indicator catalogs
- Official economic observations and explicit null values
- Provider/data-source metadata
- Data snapshots and ingestion run/audit records
- Debt-report discovery metadata
- Extracted report page/chunk text
- Tables backing freshness and country/report API endpoints

Current database-backed paths include:

- `/health` — runs `SELECT 1` through SQLAlchemy
- Country, indicator, observation, comparison and report APIs
- CSV exports
- Data freshness and coverage responses
- Debt-report discovery, processing and question endpoints
- Alembic migrations and ingestion imports

The public World Bank dashboard reads for `/api/live/world-bank/...` do **not**
write observations to the Flexible Server. Those requests call the World Bank API,
with an in-memory cache of up to five minutes, and return 2015–2025 values for the
10 dashboard indicators. Versioned snapshots and ingested provider data can still
be stored in PostgreSQL or local immutable files through separate ingestion paths.

Report handling currently combines the SQL tables above with files in
`REPORT_DATA_DIR`; it has not yet been migrated to Blob or Cosmos DB.

The `/health` response is an honest database readiness check: it reports 503 when
PostgreSQL is unavailable. Public network access is disabled on the server, so
application and development access depends on private connectivity or an explicitly
configured network path.

## Storage responsibilities

### `sovernriskai` — ADLS Gen2 data lake

Use this account for immutable, versioned and analytical datasets:

- Raw World Bank and other-provider downloads
- Bronze/Silver/Gold datasets
- Historical training snapshots
- Label workbooks and their versions
- Data manifests, hashes and lineage
- Research exports used for analysis or training

Recommended logical structure:

- `raw/` — original provider responses
- `datasets/` — immutable cleaned and feature datasets
- `manifests/` — provenance and schema records
- `exports/` — reviewed analytical outputs

This is the primary data lake for source datasets and feature development.

### `sovernriskaiv1` — Blob storage

Use this account for application and model output files:

- Azure ML managed datasets and data assets
- Training inputs and test/validation inputs
- Model artifacts and serialized experiment outputs
- The hosted frontend's private `predictions/current.json` result bundle
- Evaluation reports and metrics
- Feature schemas and model dependency metadata
- RAG development exports and generated content
- Other model-related files that need to be accessible to ML compute

The user corrected these account roles on November 17, 2026. Verify any Azure ML
datastore binding separately before running a cloud job; account purpose alone
does not establish which account `workspaceblobstore` references.

The recommended RAG split is:

- Store source PDFs and original report files in Blob Storage.
- Store report metadata and country-scoped text chunks in Cosmos DB.
- Store embeddings only when an embedding policy and account capabilities are reviewed.
- Keep model references and country predictions linked to versioned artifacts.

## Cosmos DB: intended, not current application storage

`wbgpoc-cosmosdb` is a Core SQL/NoSQL account. It is a planned target for:

- Country/report metadata
- Model-version references
- Versioned country predictions
- RAG report chunks
- Optional future embeddings

The current FastAPI and ingestion implementation still uses SQLAlchemy/PostgreSQL
and local report files. Cosmos DB SDK support is not currently wired into the
repository. Before implementation, confirm database API, throughput, containers,
partition keys and data-plane role assignments.

## Azure Machine Learning

Workspace: `sovernriskAI-diviml`

It is intended to run offline training and evaluation jobs using:

- Versioned datasets from data lake `sovernriskai`
- Model/result files in Blob account `sovernriskaiv1`, with datastore bindings verified separately
- Managed compute rather than App Service request-time training
- Reviewed artifacts exported back to versioned Blob paths

No production model, live model score or Azure ML training job is confirmed by
this README. The repository's current default-risk target remains a research
experiment until validation and serving approval are completed.

## Azure OpenAI

No Azure OpenAI or Cognitive Services resource was found in the Azure resource
inventory. RAG generation remains planned. App Service setting names do not
currently include Azure OpenAI endpoint, deployment or key settings.

## App Service deployment and configuration

The App Service currently has a `DATABASE_URL` setting, World Bank/raw-data and
CORS configuration, Application Insights settings and build settings. Never place
credentials or secrets in this README or in repository source.

The GitHub workflow builds and packages the frontend/API but deploys only through
an explicit manual `workflow_dispatch` from `main`. Source pushes do not deploy the
app. Azure publishing must remain a separate, explicit action.

## Tracking conventions

When resources or relationships change:

1. Update this inventory with the actual resource name and region.
2. Record whether public or private access is enabled.
3. Record the owner and purpose for every storage container or Cosmos container.
4. Distinguish live application behavior from planned behavior.
5. Record model versions, dataset hashes and run IDs for ML artifacts.
6. Document identity and role assignments without recording secrets.
7. Do not classify PostgreSQL, Blob, ADLS Gen2 or Cosmos data as migrated until
   application code and tests verify the change.

## Known migration boundary

The local-training feature adds an optional narrow Blob prediction adapter.
`ml.run_training` runs on the Windows laptop and exports a JSON result bundle;
an explicit publish command uploads it to existing private storage. App Service
can read it with managed identity when `PREDICTIONS_BLOB_URL` is configured.
See `docs/LOCAL_TRAINING.md`. This code path does not establish that Blob serving
is activated in Azure, and it does not migrate the remaining SQL/report storage.

The source delivery currently has:

- Active PostgreSQL/SQLAlchemy storage
- Live World Bank API reads with five-minute memory caching
- Local report files and SQL report/chunk metadata
- No production risk model
- Planned ADLS Gen2 data-lake migration
- Planned Blob-backed ML/RAG artifact storage
- Planned Cosmos DB metadata and chunk storage

Blob and Cosmos services should not be described as active application storage
until adapters, configuration and end-to-end tests are implemented.
