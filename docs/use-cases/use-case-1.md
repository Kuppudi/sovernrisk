# Use Case 1: Sovereign Early-Warning and Policy Shock Simulator

## 1) Summary
This use case helps policy and risk teams test "what happens next" before debt stress becomes a crisis. A user picks a country, sets a baseline year, applies one or more stress shocks, and gets a clear view of how sovereign default-onset risk may move. The goal is not to claim a guaranteed forecast. The goal is to give a practical early-warning tool that supports faster and better policy decisions.

In simple terms: it turns static country indicators into an interactive stress-testing workflow with transparent assumptions, caveats, and reproducible outputs.

Debt relevance: Very high. This use case directly supports sovereign debt vulnerability monitoring and policy stress testing.

## 2) Who benefits
- Ministries of Finance and debt management offices
- Multilateral and development finance analysts
- Sovereign risk teams at lenders and insurers
- Country economists and policy advisory teams

## 3) Why this should be solved
- Debt stress often escalates before institutions can respond.
- Teams need forward-looking simulations, not static snapshots.
- Current stress testing is frequently manual, inconsistent, and slow.

## 4) Core issue this solves
Decision makers do not have a consistent and evidence-grounded way to answer: "If macro conditions deteriorate, what likely happens to sovereign debt risk in this country?"

## 5) How SovereignRisk AI simplifies the issue
- Converts many indicators into one guided scenario workflow.
- Applies common shock templates so teams run comparable analyses.
- Produces risk shifts plus confidence ranges instead of a single opaque value.
- Links each scenario result to the same country fundamentals and report context already used in the app.

## 6) Detailed use-case flow
1. Analyst selects country and base date (as-of year).
2. Analyst applies one or more shock templates:
   - Commodity price shock
   - Growth slowdown
   - Inflation and interest-rate spike
   - FX/debt-service stress
3. System validates plausibility boundaries by country profile/cluster.
4. System computes scenario feature set with bounded carry-forward rules.
5. System produces:
   - Updated risk estimate
   - Direction and magnitude of change vs baseline
   - Data sufficiency and caveat flags
6. System logs scenario inputs/outputs for reproducibility and governance.

## 7) How users will use this application
No portfolio upload is required for this use case.

1. Open the existing map/dashboard and select a country.
2. Switch to a new "Scenario" panel for that country.
3. Choose a preset shock (or custom values) and run the simulation.
4. Review baseline vs stressed results side by side.
5. Read a short evidence/context explanation with sources.
6. Export the scenario result for a policy memo or committee pack.

## 8) Services we will provide
- Scenario design service (preset and custom stress templates)
- Simulation compute service (batch or near-real-time what-if inference)
- Explainability service (top changed drivers and caveats)
- Scenario history service (compare prior runs over time)
- Export/report service (policy note-ready output)

## 9) How agentic flow will be used
- Agent for scenario setup: converts user intent into structured scenario configs and validates constraints.
- Agent for simulation execution: selects the right model artifact/version and runs baseline plus stress inference.
- Agent for explanation drafting: summarizes key driver shifts and caveats in plain language.
- Agent for evidence retrieval: pulls country-scoped report context and citations for the scenario.
- Human-in-the-loop gate: user must approve final narrative/export before external sharing.

## 10) Data sources (current and planned)
Current data sources:
- World Bank WDI live API reads already used in app (`/api/live/world-bank/...`) for country fundamentals and trend context.
- Existing versioned snapshot files used for reproducible ML research inputs.
- Existing default-onset label source from the BoC-BoE sovereign default workbook used in the research pipeline.

Planned/extended sources:
- Existing ingestion connectors for IMF and ADB indicators where relevant for scenario context.
- Versioned cloud storage paths (Blob/ADLS) for durable scenario input/output archives.

## 11) Structured and unstructured data usage (and why both matter)
Structured data used:
- Country-year indicators (growth, inflation, debt-relevant series, governance metrics).
- Model inputs/outputs (baseline risk, stressed risk, deltas, confidence/caveat flags).
- Scenario configuration metadata (shock type, magnitude, run timestamp, model version).

Where structured data is used:
- Scenario calculation engine, risk comparison views, exports, and reproducibility logs.

Unstructured data used:
- Country report text (CPF, SCD, CEM, CCDR, PER, Poverty Assessment, and related documents).
- Narrative evidence describing debt stress, fiscal pressure, and financing constraints.

Where unstructured data is used:
- RAG explanation block that contextualizes scenario outputs with cited passages.

Why this benefits the use case:
- Structured data gives measurable, repeatable scenario estimates.
- Unstructured data explains why the estimate is plausible in policy context.
- Using both improves trust: users get numbers plus documented evidence.

## 12) RAG context and questions this use case should answer
RAG in this use case should explain the scenario in policy language and tie it to country evidence, for example:
- "What debt stress factors does the latest CPF/SCD mention for this country?"
- "What does recent World Bank evidence say about refinancing pressure or fiscal risk?"
- "Which report passages support why growth or inflation shocks are material here?"

RAG context inputs:
- Country ISO3 and selected scenario.
- Latest quantitative signals from the structured data layer.
- Country-scoped report chunks with page citations.

## 13) Intended libraries and technical stack
Python backend and modeling:
- fastapi: API routes for scenario execution, result retrieval, and export endpoints.
- pydantic v2: strict request/response schema validation for scenarios and outputs.
- numpy: vectorized numeric operations for feature transformation and stress calculations.
- pandas: country-year table handling, joins, and feature assembly.
- scikit-learn: baseline model inference, probability outputs, and calibration helpers.
- scipy: numerical utilities for bounded transformations and sensitivity checks.
- statsmodels (optional): transparent statistical sensitivity checks for interpretation.
- joblib: model artifact loading/caching for fast repeat inference.

Data and storage adapters:
- azure-identity: local/cloud identity auth without embedding secrets in code.
- azure-storage-blob: versioned scenario exports and artifact file reads/writes.
- azure-cosmos: scenario metadata, run history, and lightweight state records.
- httpx: calls to upstream data APIs and internal service integrations.

Frontend:
- React + TypeScript + Vite: interactive scenario controls and baseline-vs-stress visualization.
- Existing map and indicator components: country selection and scenario overlays in current UI.
- No UI redesign: reuse the current frontend layout/components and add only minimal scenario controls.

Testing and quality:
- pytest: unit/integration tests for scenario logic and API behavior.
- pytest-mock: deterministic stubbing of model and upstream dependencies.
- mypy (optional): early detection of type mismatches in pipeline interfaces.

## 14) Machine-learning principles we will use
- Keep the current research target: sovereign default onset (not a generic credit score).
- Use the existing lag policy and feature rules already in the repo (Y-2 style feature timing and bounded carry-forward).
- Keep chronological evaluation discipline (train/validation/test by time, no leakage).
- Reuse current candidate model family already tested in the project (baseline + logistic + histogram gradient boosting path).
- Treat outputs as historical/conditional research estimates, not guaranteed forecasts.
- Require minimum data sufficiency before showing numeric output and mark insufficient-data cases explicitly.
- Preserve reproducibility by versioning snapshots, model artifact references, and scenario parameters.

## 15) What these ML principles do (individually and together)
1. Target definition discipline:
  - What it does: ensures the model is solving one specific task (default onset) rather than an ambiguous risk label.
  - Problem it solves: avoids confusion and inconsistent interpretation.

2. Feature timing and lag discipline:
  - What it does: uses the same timing assumptions in training and scenario inference.
  - Problem it solves: prevents mismatch between model development logic and live demo logic.

3. Chronological split discipline:
  - What it does: evaluates on later periods than training.
  - Problem it solves: reduces look-ahead bias and leakage from future information.

4. Model-family continuity:
  - What it does: keeps the demo on model approaches already tested in this project.
  - Problem it solves: avoids unstable last-minute model changes in a short timeline.

5. Conditional-output framing:
  - What it does: presents outputs as research estimates under assumptions.
  - Problem it solves: prevents users from treating model outputs as guaranteed outcomes.

6. Data sufficiency gating:
  - What it does: blocks or flags outputs when key input coverage is too thin.
  - Problem it solves: avoids false precision from weak or sparse data.

7. Reproducibility and versioning:
  - What it does: ties every result to a known snapshot, model artifact, and scenario config.
  - Problem it solves: makes results auditable and repeatable for demos and reviews.

How they come together for the final result:
- Input quality and timing rules ensure the scenario starts from valid, consistent data.
- Evaluation rules and stable model choice keep outputs technically credible.
- Output framing and sufficiency checks keep interpretation safe and transparent.
- Versioning makes every result explainable and reproducible.
- Together, this produces a demo that is useful, trustworthy, and aligned with current project constraints.

## 16) Data and integration requirements
- Existing WDI indicators and latest-year references
- Existing label framework (default-onset research target)
- Versioned scenario metadata and run outputs
- Compatibility with current World Bank live read paths and local/offline training boundaries

## 17) Risks and controls
- Risk: unrealistic user-defined shocks.
  - Control: enforce plausibility constraints and scenario validation rules.
- Risk: overconfidence from point predictions.
  - Control: expose uncertainty bands and explicit caveats.
- Risk: misuse as a deterministic forecast.
  - Control: show research/assumption labels and policy-oriented interpretation notes.

## 18) Delivery phases (2-week demo scope)
- Phase 1 (Days 1-4): implement one baseline scenario flow for one country at a time, with two to three preset shocks and deterministic baseline-vs-stress output.
- Phase 2 (Days 5-9): add minimal UI controls for shock selection, simple result comparison, and one export format (JSON or CSV).
- Phase 3 (Days 10-14): add lightweight explanation text and one citation-backed context block; finalize demo script, test happy path, and document known limits.

## 19) Demo success criteria
- A user can run at least one scenario end to end for a selected country.
- Baseline and stressed outputs are shown side by side with clear deltas.
- One citation-backed context block appears with source traceability.
- Export works in one format and can be reused in presentation material.

## 20) Out of scope for this 2-week demo
- Full production calibration and uncertainty quantification pipeline.
- Multi-country batch simulation and enterprise-grade workflow management.
- Automated policy recommendation generation beyond simple explanatory text.
