# Use Case 1 · Local Phase 1 implementation

Updated November 24, 2026. This implements the local engine and API portion of
[Use Case 1](use-case-1.md). Real-country numerical verification is pending the
user's matching Windows model and input snapshot. Azure adapters are next;
UI/export and cited narratives remain Phases 2 and 3.

## Demo countries and evidence

Recommended examples, researched against World Bank publications on November 24:

| Country | Recent World Bank source | Why it fits this demo |
| --- | --- | --- |
| India (`IND`) | [India Development Update, October 6, 2026](https://www.worldbank.org/en/news/press-release/2026/10/06/india-development-update-oct-2026) | Strong domestic demand alongside oil-price and capital-flow risks: a useful growth/inflation sensitivity example. |
| Kenya (`KEN`) | [34th Kenya Economic Update launch, November 4, 2026](https://www.worldbank.org/en/news/press-release/2026/11/04/kenya-s-economy-is-resilient-but-stronger-governance-could-unlock-gains-in-economi) | Resilient activity alongside public-debt and interest-payment pressure: a useful financing-pressure example. [Report catalog entry](https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099110226121518967). |
| Pakistan (`PAK`) | [Pakistan Development Update launch, October 22, 2026](https://www.worldbank.org/en/news/press-release/2026/10/22/pakistan-faster-implementation-of-structural-reforms-could-see-incomes-triple-by-2) | Stabilization gains with constrained fiscal and foreign-exchange resources: a useful example of testing resilience to renewed stress. [Report](https://thedocs.worldbank.org/en/doc/ec77c491733d5748d019a1b905ef37fa-0310012026/pakistan-development-update-oct-2026-attaining-escape-velocity). |

These are demo-selection judgments, not a ranking of risk or a claim about the
model's response. Sri Lanka was also considered; its post-crisis restructuring
context makes the model's unverified no-ongoing-default assumption especially
important to resolve before a numerical default-onset demonstration.

The committed Windows bundle currently reports nine observed features and labeled
training coverage for IND, KEN and PAK, all referenced to 2025 and targeting 2027.
This establishes bundle coverage only; it does not independently validate inputs,
current default status or model calibration. The engine supports any country in
the supplied bundle, one country per request.

The report narrative and model inputs have separate provenance. Do not insert
2026 report projections into a frozen 2025 feature vector. India's and Pakistan's
fiscal-year growth measures must not be silently substituted for WDI series.
Public debt/GDP, external debt/GNI, interest/revenue and debt-service/exports are
different measures. The model uses external debt/GNI and debt-service/exports,
with their own WDI definitions; an interest/revenue figure is not a substitute
for debt-service/exports.
The links above are research references, not an implemented page-cited RAG block.

## What the engine does

1. Load operator-configured, trusted local files from one latest-research run.
2. Verify the full model SHA-256 before deserialization and recompute the snapshot
   manifest's content hash. Match these to the prediction bundle and model metadata.
3. Check scikit-learn version, class order, feature order, dates and carry-forward
   policy. Reuse `ml.features.feature_panel`; never train during a request.
4. Reconstruct the selected country's baseline, including actual source years and
   the four-feature minimum. Preserve missing values for the fitted preprocessing.
5. Apply the chosen presets only to available inputs. Re-score baseline and stress
   with the same model. Require the baseline to reproduce the frozen bundle score
   within relative tolerance 1e-9 / absolute tolerance 1e-10.
6. Return both probabilities, their difference in percentage points, all nine
   before/after feature values, source years, assumptions and reproducibility hashes.

Outputs are deterministic for identical frozen inputs and presets. Preset order
does not matter; duplicates are rejected. A stable scenario ID includes the model,
dataset, bundle and complete preset definitions. No scenario history is persisted
yet. File contents are cached in memory after validation; use immutable paths and
restart the local API whenever replacing files.

## Provisional presets, pending user agreement

| ID | Model input | Additive change |
| --- | --- | --- |
| `growth_slowdown` | GDP growth, `NY.GDP.MKTP.KD.ZG` | −2 percentage points |
| `inflation_increase` | CPI inflation, `FP.CPI.TOTL.ZG` | +3 percentage points |
| `debt_service_pressure` | Debt service / exports, `DT.TDS.DECT.EX.ZS` | +5 percentage points |

Example: growth 6% becomes 4%; inflation 4% becomes 7%; debt service equal to 20%
of exports becomes 25%. These examples are not actual country values. The
magnitudes are illustrative demo assumptions, not empirically calibrated country
plausibility limits. Custom magnitudes and historical year selection are not
exposed in Phase 1. Commodity, FX and interest-rate transmission need a separately
specified mapping or model extension.

This is conditional model sensitivity with other inputs held fixed. It does not
simulate causal policy effects, economic feedback, or the full consequences of a
crisis. Do not force stressed probabilities upward: trees can return unchanged
values and unconstrained models can return decreases. Both are preserved and
flagged. No confidence intervals or invented driver attributions are returned.

## Local setup when the artifacts arrive

Use the Windows environment that trained the artifact, including the same
scikit-learn version and compatible NumPy/pandas/joblib dependencies. If using
a fresh local environment, install the repo's normal and optional ML dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock -e ".[dev,ml]"
```

Supply these files privately, outside tracked source:

- `latest_research_model.joblib`, with its trusted source and reviewed SHA-256.
- The exact WDI snapshot archive referenced by `dataset_version`.
- The matching schema-2 `frontend_predictions.json` (the committed copy is suitable
  only if it was exported from that exact artifact).

The label workbook is not needed for inference. Do not substitute an older
`research_model.joblib` or retrain on this Mac to replace the user's Windows scores.
Joblib can execute code on load: the hash verifies integrity, not trust. There is
no model-upload endpoint. See [scikit-learn model persistence](https://scikit-learn.org/stable/model_persistence.html).

Configure the local process using actual paths:

```powershell
$env:SCENARIO_MODEL_FILE = "C:\vega-inputs\latest_research_model.joblib"
$env:SCENARIO_MODEL_SHA256 = (Get-FileHash $env:SCENARIO_MODEL_FILE -Algorithm SHA256).Hash.ToLowerInvariant()
$env:SCENARIO_SNAPSHOT_FILE = "C:\vega-inputs\wdi-snapshot.json"
$env:SCENARIO_BUNDLE_FILE = "C:\vega-inputs\frontend_predictions.json"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Computing a digest above is appropriate only after verifying the artifact's source.
The API imports ML dependencies lazily. Ordinary app startup and preset listing
work without them. Scenario requests need no SQL, Blob, Cosmos or generation
credentials. Existing SQL-backed `/health` still checks PostgreSQL and can report
unavailable independently; this feature does not migrate it.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/scenarios/presets
$body = @{ country_iso3 = "IND"; presets = @("growth_slowdown") } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/scenarios -Method Post -ContentType "application/json" -Body $body
```

Repeat with `KEN` and `PAK`. All three selected presets may be combined in one
request. The API obtains dates from the frozen run; a 2026 run uses 2025 reference
inputs and the existing 2027 outcome target, not a new immediate-risk forecast.

Missing configuration returns `SCENARIO_NOT_CONFIGURED` (503). Missing/incompatible
files return `SCENARIO_ARTIFACT_UNAVAILABLE` (503). Unsupported country returns 404;
insufficient coverage, missing shocked inputs and invalid preset selection return
422. Failed baseline reproduction returns `BASELINE_MISMATCH` (503). No fallback
to another artifact, live WDI data or invented result occurs.

## Verification and remaining phases

Synthetic tests exercise baseline reproduction, input integrity, timing, missing
inputs, combined shocks, unchanged features, decreasing outputs, invalid model
outputs, and the API without database/cloud calls. An integration check uses the
actual `train` → `latest_estimates` export pipeline with isolated synthetic data.

```powershell
.\.venv\Scripts\python.exe -m pytest -q ml/tests backend/tests/test_scenarios.py
```

Local real-country acceptance remains pending artifacts: reproduce IND, KEN and
PAK baselines, run the three presets, and inspect the actual response, including
unchanged or counterintuitive results. Do not claim this check passed from bundle
coverage or synthetic tests alone.

Next: agree preset assumptions, supply artifacts and verify local real-country
results, then connect existing Azure storage. Phase 2 adds minimal UI and one
export format. Phase 3 adds deterministic explanation plus retrieved page citations
or Foundry narrative, with the generation approach still undecided. Foundry would
write text from model results and retrieved evidence; it would not calculate or
change the probabilities. No model artifacts or ML runtime have been added to the
App Service ZIP, and no Azure resources, settings or deployment are changed here.
