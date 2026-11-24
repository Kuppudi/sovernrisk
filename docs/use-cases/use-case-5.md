# Use Case 5: Portfolio-Level Sovereign Risk Management

## 1) Summary
This use case helps institutions that hold exposure across many countries understand total downside risk, not just one country at a time. A user uploads or selects a portfolio, runs stress scenarios, and sees concentration, tail risk, and possible rebalancing choices. The output supports stronger risk governance and clearer decision-making.

In simple terms: it translates country risk signals into portfolio-level decisions.

Debt relevance: Very high. This use case is directly tied to sovereign debt exposure management.

## 2) Who benefits
- Portfolio and risk managers with sovereign exposure
- Treasury and strategy teams
- Development finance allocation committees
- Insurance and guarantee program managers

## 3) Why this should be solved
- Single-country analysis does not show whole-portfolio downside.
- Correlations and concentration can hide tail risk.
- Committees need defensible stress-based allocation guidance.

## 4) Core issue this solves
Organizations with multi-country sovereign exposure lack a transparent way to estimate portfolio loss concentration and stress vulnerability from sovereign debt deterioration.

## 5) How SovereignRisk AI simplifies the issue
- Aggregates country-level risk into a portfolio view.
- Simulates portfolio stress under consistent scenarios.
- Highlights where exposure reduction or rebalancing may reduce downside risk.

## 6) Detailed use-case flow
1. User uploads exposure table (country, amount/weight, tenor if available).
2. System maps exposures to country risk signals and dependencies.
3. User applies baseline and stress scenarios.
4. Engine computes:
   - Concentration heatmap
   - Stress loss distribution
   - Tail-risk indicators (for example VaR/CVaR style metrics)
5. System suggests risk-reduction alternatives under user constraints.

## 7) How users will use this application
1. Go to the portfolio workspace in the app.
2. Upload portfolio exposure data or choose a saved portfolio.
3. Select baseline and stress scenarios.
4. Review concentration and downside-risk outputs.
5. Inspect suggested adjustments and expected risk reduction.
6. Export a governance-ready report for committee review.

## 8) Services we will provide
- Exposure ingestion and validation service
- Portfolio stress simulation service
- Tail-risk analytics service
- Allocation recommendation service (constraint-aware)
- Governance reporting service for decision committees

## 9) How agentic flow will be used
- Agent for portfolio intake: validates upload schema and resolves country mappings.
- Agent for stress orchestration: runs selected scenarios and aggregates portfolio outcomes.
- Agent for recommendation drafting: proposes rebalancing options under defined constraints.
- Agent for evidence linking: connects top exposure risks to country-level report context.
- Human-in-the-loop gate: user reviews and approves recommendations before use in decisions.

## 10) Data sources (current and planned)
Current data sources:
- Country-level macro and risk context already available in the app.
- Existing research-model outputs where available.
- User-provided portfolio exposure files.

Planned/extended sources:
- Cosmos metadata for saved portfolios and run history.
- Blob for archived portfolio scenario outputs and report packs.
- Optional linkage data to improve correlation assumptions in stress scenarios.

## 11) Structured and unstructured data usage (and why both matter)
Structured data used:
- Portfolio exposures, country mappings, scenario parameters, and stress-output metrics.
- Concentration, downside indicators, recommendation rules, and run metadata.

Where structured data is used:
- Portfolio analytics engine, recommendation logic, and governance reporting.

Unstructured data used:
- Country report evidence describing macro/fiscal risks in top-exposure markets.
- Narrative summaries that explain recommendation rationale to committees.

Where unstructured data is used:
- RAG-backed explanation layer for top risk contributors and rebalance suggestions.

Why this benefits the use case:
- Structured data gives objective portfolio math and comparable scenarios.
- Unstructured data gives decision-makers the policy/economic context behind recommendations.
- Using both improves decision transparency for committee review.

## 12) RAG context and questions this use case should answer
RAG in this use case should help explain portfolio concentration and scenario impact, for example:
- "Which country-level risk factors are driving most portfolio downside?"
- "What country report evidence supports concern in top exposure markets?"
- "What policy or macro signals in reports justify the recommended rebalance?"

RAG context inputs:
- Portfolio composition and top-exposure countries.
- Scenario outputs and tail-risk decomposition.
- Country report chunks with citations for top contributors.

## 13) Intended libraries and technical stack
Python analytics:
- fastapi
- pydantic v2
- pandas
- numpy
- scipy
- scikit-learn
- cvxpy (optional constrained optimization)
- matplotlib/plotly for backend-generated report graphics (optional)

Data/storage:
- azure-cosmos (portfolio configs and run metadata)
- azure-storage-blob (scenario reports and archived outputs)
- azure-identity

Frontend:
- Existing React dashboard extended with portfolio views and upload flow

Testing:
- pytest
- deterministic scenario regression tests

## 14) Machine-learning principles we will use
- Portfolio view over single-score view: evaluate concentration and correlation, not only country-level point estimates.
- Scenario-based risk estimation: compare baseline and stressed outcomes under consistent assumptions.
- Uncertainty-aware reporting: present ranges and sensitivity, not false precision.
- Constraint-aware optimization: recommendations must honor practical rules (exposure limits, policy constraints).
- Explainability of recommendations: show which countries/factors drive each suggested adjustment.
- Reproducibility: version exposure inputs, scenario configs, and recommendation logic.

## 15) Data and integration requirements
- Country-level risk estimates and metadata
- Exposure dataset schema and validation rules
- Scenario definitions and optional correlation assumptions
- Historical run archive for governance and reproducibility

## 16) Risks and controls
- Risk: false precision in loss metrics.
  - Control: range-based reporting, caveats, and sensitivity outputs.
- Risk: weak data quality from uploaded exposures.
  - Control: strict schema validation and completeness checks.
- Risk: recommendation misuse as automated decisioning.
  - Control: human-in-the-loop review and explainable recommendation rationale.

## 17) Delivery phases (2-week demo scope)
- Phase 1 (Days 1-4): implement portfolio upload validation and baseline concentration view for a small demo dataset.
- Phase 2 (Days 5-9): add one stress scenario and one downside metric view (simple tail-risk approximation).
- Phase 3 (Days 10-14): add one recommendation panel with transparent rules and one evidence-linked narrative summary for top exposures.
