# Azure Services and Foundry Integration Plan

## 1) Purpose
This document explains which Azure services are currently in use, which are planned, how each use case connects to the services, and how Foundry should be used in a controlled way.

It is aligned with the current repository state and Azure inventory. It is not deployment authorization.

## 2) Current Azure stack (as confirmed)
Active/confirmed:
- Azure App Service: `sovernriskAI` (frontend + FastAPI hosting)
- App Service Plan: `ASP-wbgpocrg-afce`
- PostgreSQL Flexible Server: `sovernriskai-server` (current SQL-backed runtime paths remain)
- ADLS Gen2 account: `sovernriskai` (data lake role)
- Blob Storage account: `sovernriskaiv1` (prediction/model/report file role)
- Cosmos DB NoSQL account: `wbgpoc-cosmosdb` (planned target for metadata/chunks/predictions)
- Azure ML workspace: `sovernriskAI-diviml` (available for future managed ML jobs)
- Application Insights: `sovernriskAI`
- Key Vault: `wbgpocrgsovdiv6922738757`

Important boundary:
- App currently serves World Bank live data via API paths and keeps many persisted/report paths in SQL.
- Blob prediction adapter exists for result bundle loading when configured.
- Full Blob/Cosmos migration remains planned, not fully implemented.

## 3) Foundry status and usage approach
Known account:
- `wbgpoc-foundry` exists in the resource group, but current project docs state it is not yet treated as an active application dependency.

How Foundry should be used:
1. Keep Foundry in planned/controlled scope until ownership and deployment readiness are confirmed.
2. Use Foundry for AI generation workloads only after:
   - identity and access are validated,
   - retrieval grounding is enforced,
   - citation quality controls are enabled.
3. Connect Foundry generation only to approved retrieval context:
   - country-scoped report chunks,
   - current model/status metadata,
   - dated structured-data context.

Where Foundry connects:
- Input path:
  - Cosmos report chunk metadata and references
  - Blob-backed report/PDF provenance
  - App Service request context (country, question, selected timeframe)
- Output path:
  - Structured response with citations returned to App Service API
  - Logged metadata for observability (no sensitive content leakage)

## 4) Service responsibility model
App Service:
- API orchestration and frontend delivery
- Runtime validation, response formatting, caching

ADLS Gen2 (`sovernriskai`):
- Raw and curated dataset history
- Versioned manifests and lineage records

Blob (`sovernriskaiv1`):
- Prediction bundles and model artifacts
- Report files and processed extraction assets

Cosmos DB (`wbgpoc-cosmosdb`):
- Country/report metadata
- Report chunks and retrieval metadata
- Model-version pointers and prediction metadata

Azure ML (`sovernriskAI-diviml`):
- Offline training/evaluation on managed compute
- Artifact export to Blob

Foundry/Azure OpenAI:
- Citation-grounded generation layer for the future AI card

Application Insights + Key Vault:
- Telemetry, diagnostics, secure configuration management

## 5) How each use case maps to Azure services
Use case 1: Early-warning and policy shock simulator
- Compute/orchestration: App Service
- Scenario inputs and output archives: Blob + Cosmos
- Optional retraining: Azure ML
- Optional narrative summary: Foundry (future)

Use case 2: Debt vulnerability triage system
- Triage API and ranking delivery: App Service
- Historical triage state: Cosmos
- Exports and governance artifacts: Blob
- Data preparation cadence: Azure ML jobs (optional)

Use case 3: Evidence-grounded risk briefing generator
- Retrieval and API: App Service
- PDFs and extracted pages: Blob
- Chunk/citation metadata: Cosmos
- Generation: Foundry/Azure OpenAI (with strict citation constraints)

Use case 4: Cross-country contagion monitor
- Simulation service: App Service
- Graph metadata and scenario states: Cosmos
- Batch scenario outputs: Blob
- Optional retraining/calibration: Azure ML

Use case 5: Portfolio-level sovereign risk management
- Exposure ingestion and simulation API: App Service
- Portfolio run metadata: Cosmos
- Report artifacts and downloadable packs: Blob
- Optional optimization calibration jobs: Azure ML

## 6) Implementation patterns and connection points
Identity and security:
- Use Managed Identity in hosted environments.
- Use Azure CLI-backed identity for local development.
- Keep secrets in Key Vault and App Service settings.

Data access:
- Keep explicit partition scoping in Cosmos for country-level isolation.
- Use immutable Blob paths with version identifiers and hashes.

Observability:
- Track model/scenario version metadata in logs and response payloads.
- Use Application Insights for latency/error and retrieval diagnostics.

Reliability:
- Use write-completion protocols where Blob and Cosmos writes span multiple steps.
- Expose incomplete version states as unavailable, never as silently usable.

## 7) Recommended Python/Azure libraries for service integration
Core backend:
- fastapi
- pydantic v2
- uvicorn

Azure SDKs:
- azure-identity
- azure-storage-blob
- azure-cosmos
- azure-keyvault-secrets
- azure-monitor-opentelemetry (or equivalent telemetry integration)

ML and analytics:
- pandas
- numpy
- scikit-learn
- scipy
- joblib

RAG/retrieval support:
- pypdf or pymupdf
- bm25-compatible retrieval library
- optional semantic-kernel style orchestration

Testing:
- pytest
- pytest-asyncio
- unittest.mock/pytest-mock

## 8) Guardrails for real-world rollout
- Do not represent research estimates as production credit decisions.
- Keep explicit labels for model scope, date, and data sufficiency.
- Require evidence citations for generated narratives.
- Separate planned architecture from currently live behavior in all docs/UI.
- Keep deployment manual and approval-based per project policy.

## 9) Suggested sequence
1. Finalize use-case-specific APIs and schemas.
2. Strengthen Blob/Cosmos adapters and version-state handling.
3. Roll out triage and scenario services first (lower generation risk).
4. Add Foundry-backed briefing generation with strict citation validation.
5. Expand to contagion and portfolio optimization workflows.
