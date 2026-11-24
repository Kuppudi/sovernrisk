# Use Case 4: Cross-Country Contagion and Spillover Monitor

## 1) Summary
This use case helps teams see how one country's stress can affect other countries. A user can apply a shock to one country or region and view where pressure is likely to spread next. Instead of treating each country as isolated, the app shows likely spillover paths and which countries may need earlier monitoring.

In simple terms: it helps teams detect second-order debt and macro risk before it appears directly in every country.

Debt relevance: Medium-high. Debt is a key transmission channel, but the framework also uses broader macro linkages.

## 2) Who benefits
- Regional policy and risk teams
- Development partners planning cross-country interventions
- Lenders with regional sovereign exposure
- Early-warning and surveillance units

## 3) Why this should be solved
- Sovereign stress is often contagious rather than isolated.
- Country-by-country monitoring misses second-order effects.
- Regional planning requires visibility into spillover pathways.

## 4) Core issue this solves
Institutions cannot easily identify which countries may become newly vulnerable because another country or region experiences debt stress.

## 5) How SovereignRisk AI simplifies the issue
- Converts complex interdependencies into a practical network view.
- Simulates shock propagation from one or more origin countries.
- Highlights next-most-vulnerable countries and likely channels.

## 6) Detailed use-case flow
1. Build country dependency graph from selected channels:
   - Regional adjacency
   - Trade linkage (if available)
   - Financing/refinancing conditions
   - Macro co-movement signatures
2. User selects origin country and shock magnitude.
3. Engine computes first-order and second-order spillovers.
4. UI shows affected countries and impact intensity.
5. System emits prioritized watchlist and caveats.

## 7) How users will use this application
1. Open the contagion workspace from the dashboard.
2. Pick an origin country (or small set of countries) and a shock level.
3. Run propagation and review affected countries on the map/list.
4. Inspect channel explanations (regional, financing, macro linkage).
5. Save scenario results and compare with earlier runs.
6. Export an action watchlist for regional review meetings.

## 8) Services we will provide
- Dependency graph construction service
- Spillover simulation service
- Vulnerability ranking service
- Regional watchlist service
- Scenario comparison service across multiple origin shocks

## 9) How agentic flow will be used
- Agent for graph assembly: builds and updates country-link structures from configured channels.
- Agent for scenario execution: runs propagation from selected origin shock settings.
- Agent for impact explanation: summarizes why each affected country moved in risk priority.
- Agent for regional brief drafting: produces concise watchlist notes with evidence links.
- Human-in-the-loop gate: user confirms assumptions/channels before sharing outputs.

## 10) Data sources (current and planned)
Current data sources:
- Country macro and debt-relevant indicators from existing WDI data flows.
- Existing country metadata and risk context from current app paths.

Planned/extended sources:
- IMF/ADB indicator extensions for external vulnerability signals.
- Optional external linkage datasets (trade/financial connectivity) for stronger graph edges.
- Cosmos-stored graph metadata and scenario outputs.

## 11) Structured and unstructured data usage (and why both matter)
Structured data used:
- Country indicators, graph edges/weights, shock parameters, and propagation outputs.
- Ranked impact scores, channel-level decompositions, and scenario comparison metadata.

Where structured data is used:
- Spillover engine, map/list ranking, and saved scenario comparisons.

Unstructured data used:
- Country and regional report passages describing cross-border dependencies and financing vulnerabilities.
- Narrative context for explaining likely transmission paths.

Where unstructured data is used:
- RAG explanation layer that interprets why specific spillovers are credible.

Why this benefits the use case:
- Structured data quantifies spillovers and supports reproducible ranking.
- Unstructured data explains mechanisms and policy relevance.
- Using both prevents "black-box" spillover outputs.

## 12) RAG context and questions this use case should answer
RAG in this use case should provide regional interpretation and evidence, for example:
- "Why is this neighboring country sensitive to the origin shock?"
- "What report evidence indicates shared refinancing or fiscal pressure in this region?"
- "Which country documents mention cross-border economic or financing dependencies?"

RAG context inputs:
- Origin country, affected country, and selected shock.
- Graph channel outputs and impact ranking.
- Country/region report chunks and citations.

## 13) Intended libraries and technical stack
Python modeling:
- fastapi
- pydantic v2
- numpy
- pandas
- networkx (graph construction and propagation)
- scipy (matrix operations and stability checks)
- scikit-learn (optional clustering and similarity features)

Storage and integration:
- azure-cosmos (graph metadata and scenario outputs)
- azure-storage-blob (versioned scenario runs and exports)
- azure-identity

Frontend:
- Existing React map foundation
- Optional graph visualization library in frontend for network overlay

Testing:
- pytest
- property-based tests for propagation bounds

## 14) Machine-learning principles we will use
- Network-aware modeling: represent dependencies explicitly instead of independent country scoring only.
- Bounded propagation: constrain spillover dynamics to avoid unstable or unrealistic amplification.
- Sensitivity analysis: test how outputs change under different channel weights.
- Explainability by channel: attribute impact to regional, financing, or macro pathways.
- Robustness checks: compare graph outputs to simpler baselines to avoid overfitting complexity.
- Reproducibility: version graph definitions, channel weights, and scenario seeds.

## 15) Data and integration requirements
- Country economic indicators and risk inputs
- Region/country metadata and standardized identifiers
- Optional external linkage datasets (trade/financial channels)
- Versioned graph definitions and simulation parameters

## 16) Risks and controls
- Risk: inferred links mistaken as causal proof.
  - Control: clearly label channel assumptions and confidence levels.
- Risk: unstable propagation with sparse inputs.
  - Control: conservative damping factors and strict bounds.
- Risk: over-complex visual outputs.
  - Control: default to ranked impact lists with optional advanced graph view.

## 17) Delivery phases (2-week demo scope)
- Phase 1 (Days 1-4): implement adjacency-based spillover baseline with one origin country and map/list affected-country output.
- Phase 2 (Days 5-9): add one additional channel (for example macro similarity) and simple impact ranking/decomposition.
- Phase 3 (Days 10-14): add one saved-scenario comparison view and short RAG-backed regional explanation block with citations.
