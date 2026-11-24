# Use Case 2: Debt Vulnerability Triage System

## 1) Summary
This use case gives teams a practical way to decide where to focus first when they cannot review every country deeply. The app creates a debt-risk work queue that ranks countries by urgency and explains what changed since the previous review cycle. Instead of a broad dashboard that everyone reads differently, this becomes a clear weekly or monthly action list.

In simple terms: it helps teams spend limited time on the countries with the highest debt-vulnerability urgency.

Debt relevance: Very high. This use case is directly about sovereign debt distress prioritization.

## 2) Who benefits
- Sovereign debt management offices
- World Bank and other multilateral country teams
- Development finance risk committees
- Policy operations and technical assistance planners

## 3) Why this should be solved
- Teams monitor many countries with limited resources.
- Risk review cycles can become reactive and inconsistent.
- Without triage, worsening debt conditions may be missed.

## 4) Core issue this solves
Institutions lack a transparent and repeatable way to decide which countries require immediate debt-risk review this week or month.

## 5) How SovereignRisk AI simplifies the issue
- Converts broad monitoring into a ranked work queue with clear urgency levels.
- Standardizes triage logic across teams.
- Shows why a country moved up or down in rank since the last cycle.

## 6) Detailed use-case flow
1. Ingest latest country-level economic and risk-relevant signals.
2. Compute triage score from weighted factors:
   - Risk level
   - Risk change velocity
   - Data completeness and recency
   - Governance/stability proxies
3. Assign operational labels: High, Medium, Watchlist.
4. Produce "what changed" explanation for each country.
5. Trigger alerts for threshold crossings.
6. Export weekly/monthly triage pack.

## 7) How users will use this application
1. Open the dashboard and choose the triage workspace.
2. View ranked countries by urgency with filters (region, risk band, data quality).
3. Click a country to see why its rank moved up or down.
4. Assign country reviews to analysts and set review due dates.
5. Export the queue and supporting notes for internal meetings.
6. Track which countries were reviewed and what actions were taken.

## 8) Services we will provide
- Triage scoring service
- Rank movement explanation service
- Alerting and threshold service
- Worklist assignment service for analyst teams
- Audit and reproducibility service for governance review

## 9) How agentic flow will be used
- Agent for triage scoring: computes urgency ranks from current signals and policy thresholds.
- Agent for movement analysis: explains rank changes compared with prior review cycles.
- Agent for alerting: identifies threshold crossings and drafts action-oriented notifications.
- Agent for assignment support: proposes analyst work allocation based on workload and region.
- Human-in-the-loop gate: user confirms final queue and assignments before distribution.

## 10) Data sources (current and planned)
Current data sources:
- World Bank WDI live reads for current macro and debt-relevant context.
- Versioned local/cloud snapshots used by the ML research pipeline.
- Existing research-model outputs where available.

Planned/extended sources:
- IMF and ADB series already in ingestion scope for fiscal and debt-flow context.
- Country metadata and workflow events stored in Cosmos for triage state/history.

## 11) Structured and unstructured data usage (and why both matter)
Structured data used:
- Country-level risk indicators, trend deltas, recency, and data-quality fields.
- Triage score components, urgency labels, threshold states, and movement history.
- Operational workflow data (assignment status, review cycles, alert timestamps).

Where structured data is used:
- Ranking engine, filters, alerting rules, and audit trail exports.

Unstructured data used:
- Country report passages that explain debt-service pressure and policy constraints.
- Analyst notes or generated handoff summaries linked to ranked countries.

Where unstructured data is used:
- RAG-backed "why this is urgent" snippets and handoff context panels.

Why this benefits the use case:
- Structured data provides objective prioritization and comparability.
- Unstructured data adds real-world context for action decisions.
- Using both reduces false urgency and improves review quality.

## 12) RAG context and questions this use case should answer
RAG in this use case should support triage justification and handoff context, for example:
- "Why is this country now in High priority?"
- "Which recent report passages describe rising debt-service pressure?"
- "What policy risks were highlighted in the latest country strategy documents?"

RAG context inputs:
- Country ISO3 and current triage rank.
- Rank movement reasons and key indicator deltas.
- Country-scoped report chunks with citations and dates.

## 13) Intended libraries and technical stack
Python backend:
- fastapi
- pydantic v2
- pandas
- numpy
- scikit-learn (for ranking/weighting calibration)
- sqlalchemy (for legacy paths that remain SQL-backed)

Azure/data integration:
- azure-cosmos (country-state metadata and triage state)
- azure-storage-blob (versioned exports and manifests)
- azure-identity

Workflow/operations:
- apscheduler or Azure-native scheduling integration
- python-dateutil
- tenacity (retry and resilience)

Testing:
- pytest
- hypothesis (optional score stability and rule-property testing)

## 14) Machine-learning principles we will use
- Ranking before prediction complexity: start with transparent score decomposition, then add learned weighting only when justified.
- Stability over noise: apply smoothing and movement thresholds so minor data revisions do not create false urgency jumps.
- Fairness under missingness: separate data-quality signals from risk signals to avoid penalizing low-data countries.
- Explainability-first outputs: every rank change should map to measurable input changes.
- Drift monitoring: detect when triage behavior changes due to source or model drift and trigger review.
- Reproducibility: store scoring version, inputs, and thresholds for each triage cycle.

## 15) Data and integration requirements
- Country fundamentals and observed trajectories
- Existing research risk outputs (where available)
- Country-level metadata for grouping and assignment
- Historical triage snapshots for trend and audit

## 16) Risks and controls
- Risk: triage bias due to sparse-data countries.
  - Control: separate data-quality score and explicit uncertainty labels.
- Risk: score volatility due to minor data updates.
  - Control: movement thresholds and smoothing rules.
- Risk: low trust from opaque weighting.
  - Control: transparent score decomposition and reviewable weights.

## 17) Delivery phases (2-week demo scope)
- Phase 1 (Days 1-4): implement deterministic triage score and ranked country list with one default weighting profile.
- Phase 2 (Days 5-9): add filters (for example region and urgency), one movement/explainer panel, and CSV export for review meetings.
- Phase 3 (Days 10-14): add basic threshold alerts and one concise RAG-backed justification snippet per country; finalize demo data, walkthrough, and limitations.

## 18) Demo success criteria
- Ranked country queue is generated reproducibly from the same input snapshot.
- Users can filter, inspect one country explanation, and export the queue.
- At least one threshold-crossing alert scenario is demonstrable.
- RAG-backed urgency justification is shown for at least one selected country.

## 19) Out of scope for this 2-week demo
- Full assignment workflow automation and team collaboration tooling.
- Advanced online learning/retraining loop for triage scoring.
- Deep governance analytics beyond essential audit fields.
