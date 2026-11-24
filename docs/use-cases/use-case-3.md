# Use Case 3: Evidence-Grounded Risk Briefing Generator

## 1) Summary
This use case creates briefing-ready country debt-risk notes that combine numbers and evidence in one place. A user selects a country and focus topic, and the app returns a structured briefing with claims tied to report citations. The main benefit is speed with trust: analysts can prepare decision notes faster without losing source traceability.

In simple terms: it turns scattered report reading and manual note writing into a fast, citation-backed country briefing workflow.

Debt relevance: High. It directly supports debt-risk interpretation and communication with source citations.

## 2) Who benefits
- Country economists and debt analysts
- Government and donor policy teams
- Credit and risk committees
- Senior stakeholders who need explainable briefings quickly

## 3) Why this should be solved
- Briefing production is often manual and slow.
- Important claims are difficult to trace to evidence.
- Teams need fast synthesis without sacrificing rigor.

## 4) Core issue this solves
Institutions need concise, trustworthy, and source-cited debt-risk briefings but currently spend significant analyst time collecting and reconciling evidence from many long reports.

## 5) How SovereignRisk AI simplifies the issue
- Retrieves relevant country passages from official reports.
- Grounds generated text in retrieved evidence and model context.
- Produces standardized briefing structure with citations and caveats.

## 6) Detailed use-case flow
1. User selects country and briefing focus (debt sustainability, growth constraints, public spending pressure).
2. System retrieves relevant passages from indexed report corpus.
3. System gathers model status and latest quantitative context.
4. Generator creates briefing sections:
   - Current signal summary
   - Key debt risk drivers
   - Supporting evidence with citations
   - Data and model caveats
5. User reviews citations and exports report.

## 7) How users will use this application
1. Choose a country and a briefing template (for example debt sustainability update).
2. Select timeframe and document types to include.
3. Run "Generate briefing" and inspect sections with inline citations.
4. Open cited passages and verify relevance.
5. Edit summary text if needed and export for policy or committee use.
6. Save the run for later comparison with future briefings.

## 8) Services we will provide
- Report retrieval service (country-scoped and document-type aware)
- Evidence ranking service (BM25 now, optional vector retrieval later)
- Briefing generation service with citation constraints
- Citation validation service (source/page integrity checks)
- Export service (JSON, markdown, PDF-ready)

## 9) How agentic flow will be used
- Agent for retrieval planning: interprets briefing objective and builds document/query plan.
- Agent for evidence collection: retrieves and ranks country-scoped passages with citations.
- Agent for synthesis: drafts structured briefing sections grounded in selected evidence.
- Agent for validation: checks citation presence, country alignment, and unsupported claims.
- Human-in-the-loop gate: user reviews citations and approves final briefing export.

## 10) Data sources (current and planned)
Current data sources:
- Official country/project report corpus already targeted in the project (ISR, ESRS, CPF, SCD, CEM, CCDR, PER, Poverty Assessment).
- Country fundamentals and model-status context from the app's structured data paths.
- Existing report metadata and chunking/indexing groundwork in the backend.

Planned/extended sources:
- Blob for original PDFs and processed page assets.
- Cosmos for chunk metadata, retrieval indexes, and citation references.

## 11) Structured and unstructured data usage (and why both matter)
Structured data used:
- Country metrics, model-status fields, dates, and briefing metadata.
- Retrieval scores, citation IDs, document dates, and export audit fields.

Where structured data is used:
- Briefing templates, section ordering, filtering, and consistency validation.

Unstructured data used:
- Full-text report passages from ISR, ESRS, CPF, SCD, CEM, CCDR, PER, and Poverty Assessment documents.
- Narrative context extracted from PDF pages and chunks.

Where unstructured data is used:
- Retrieval engine and generation context for evidence-grounded briefing text.

Why this benefits the use case:
- Structured data keeps the briefing format consistent and checkable.
- Unstructured data supplies substantive country evidence and nuance.
- Using both enables fast output without losing traceability.

## 12) RAG context and questions this use case should answer
RAG in this use case is the core engine and should answer questions like:
- "What evidence supports rising debt vulnerability in this country?"
- "What fiscal, growth, or governance constraints are repeatedly cited?"
- "What changed between older and newer country strategy/economic reports?"

RAG context inputs:
- Country, period, and briefing objective.
- Retrieved report chunks with page/citation metadata.
- Current structured risk context and model availability status.

## 13) Intended libraries and technical stack
Python backend and retrieval:
- fastapi
- pydantic v2
- rank-bm25 or tantivy/Whoosh-style retrieval tooling
- nltk or spacy (optional text processing)
- pypdf or pymupdf for PDF extraction paths

Azure integration:
- azure-cosmos (report chunk metadata)
- azure-storage-blob (PDF and extracted text assets)
- azure-identity

Generation/orchestration:
- Azure OpenAI SDK path via REST or official client wrappers
- Structured output validation with pydantic
- Optional orchestration frameworks: semantic-kernel or lightweight internal orchestrator

Frontend:
- Existing React app for citation display and evidence panel

Testing:
- pytest
- snapshot-based response tests for citation consistency

## 14) Machine-learning principles we will use
- Grounded generation only: no final claim without supporting retrieved evidence.
- Retrieval quality first: optimize ranking relevance before increasing generation complexity.
- Structured outputs: enforce schema-validated sections to reduce freeform error propagation.
- Citation faithfulness checks: verify that generated statements are supported by cited passages.
- Temporal awareness: prioritize recent authoritative documents while preserving historical comparison.
- Evaluation loop: measure retrieval precision, citation validity rate, and human-acceptance rate.

## 15) Data and integration requirements
- Report types already identified for country/project context:
  - ISR
  - ESRS
  - CPF
  - SCD
  - CEM
  - CCDR
  - PER
  - Poverty Assessment
- Country metadata and document provenance
- Page-level citation references and stable document IDs

## 16) Risks and controls
- Risk: hallucinated statements.
  - Control: citation-first generation constraints and response validation.
- Risk: stale evidence usage.
  - Control: date-aware retrieval and report-version metadata.
- Risk: mixed-context errors across countries.
  - Control: strict ISO3/country partition scoping.

## 17) Delivery phases (2-week demo scope)
- Phase 1 (Days 1-4): deliver retrieval-only evidence panel for one country at a time with visible citations and source links.
- Phase 2 (Days 5-9): add structured briefing draft generation with fixed sections and mandatory citation formatting.
- Phase 3 (Days 10-14): add reviewer edit/export flow (markdown or PDF-ready text), plus basic validation to block unsupported claims in demo outputs.

## 18) Demo success criteria
- User can generate a structured briefing draft for one selected country.
- Every major claim in the draft has at least one visible citation.
- Reviewer can edit and export briefing output in one supported format.
- Validation blocks at least one intentionally unsupported claim in testing.

## 19) Out of scope for this 2-week demo
- Full contradiction-resolution engine across all document vintages.
- Enterprise-grade evaluation dashboards and long-term quality telemetry.
- Broad multi-country batch briefing generation pipeline.
