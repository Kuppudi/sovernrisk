# Local ML training and hosted prediction results

Run training on the Windows laptop. With no Blob upload role, include the result
JSON in the App Service deployment ZIP by committing the reviewed file at
`deploy/frontend_predictions.json`, or using the explicit local packaging option.
App Service discovers that file automatically for the map and country card.
Blob publishing remains an optional alternative when the caller has access.
Training needs neither Docker nor a database nor an Azure ML compute job.
The app's other stored-data/report paths currently retain their SQL dependency.

The default command now produces **latest-data conditional research estimates**
for the full World Bank country/economy catalog. It first evaluates chronological
historical partitions, then refits the selected learner on all eligible labeled
years available in the snapshot and scores each catalog country separately.
A country does not need a historical label to receive an estimate, but estimates
outside labeled-country coverage are explicitly marked.

The feature reference year is the last complete calendar year. With the existing
two-year outcome lag, a run as of November 2026 uses a 2025 feature reference year
and a 2027 forecast year. Inputs can carry forward by at most two years, using the
same policy in evaluation and scoring. Each result records actual input years.
At least four of nine recent features are required. All catalog economies appear
in the JSON; those below that minimum have a null score and Insufficient data.

These estimates assume no ongoing default at forecast origin. Current default
status is unverified, revised historical vintages remain a limitation, and model
calibration is incomplete. They are research estimates rather than validated
lending forecasts. AI / RAG stays Coming soon.

## 1. Get the source and install on Windows

From the repository root in the VS Code PowerShell terminal, fetch and check out
the delivery branch while preserving existing work. After it is merged, use main.

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock -e ".[ml]"
```

## 2. Download and train on the laptop

```powershell
.\.venv\Scripts\python.exe -m ml.run_training --download-inputs
```

This downloads global WDI data from 1960 through the last complete year and the
official BoC–BoE workbook. Evaluation, full-history refitting and catalog scoring
run on the laptop CPU. It
does not submit a cloud job, write SQL or upload results. Allow time for provider
downloads. The frontend's economic display window remains 2015–2025.

Outputs under ignored `ml/artifacts/default-onset/` include `metrics.json`,
`research_model.joblib` and `historical_test_predictions.csv` for evaluation,
plus `latest_research_model.joblib`, `latest_research_metadata.json` and
`frontend_predictions.json` for latest estimates. Keep source datasets and generated outputs out of
Git, with the single reviewed JSON copy under `deploy/` as the user-approved exception.

For subsequent runs, reuse the downloaded files:

```powershell
.\.venv\Scripts\python.exe -m ml.run_training
```

To reuse different existing files:

```powershell
.\.venv\Scripts\python.exe -m ml.run_training `
  --snapshot "C:\vega-inputs\wdi-snapshot.json" `
  --default-workbook "C:\vega-inputs\BoC-BoE-Database-2026.xlsx"
```

For the historical held-out export only, rather than latest-data estimates:

```powershell
.\.venv\Scripts\python.exe -m ml.prediction_bundle export `
  --snapshot "data/raw/global-wdi-1960-2025.json" `
  --output "ml/artifacts/default-onset"
```

Latest bundles use schema 2 and contain one row per catalog country, with score
availability, feature years/count and labeled-country coverage. Historical
schema-1 bundles remain readable. The latest full-history artifact is separate
from the pre-refit artifact and test metrics. The old test metrics must not be
reported as evaluating the full-history fit.

The risk palette uses fixed presentation bands: green below 10%, yellow from
10% to below 50%, red at 50% or above. Labels say lower/elevated/higher model
estimate. These are display bands, not validated credit categories or claims
that a red country will default. GDP growth retains its independent blue scale.
See [2025 data and source accuracy](DATA_SOURCES_2025.md) before adding substitutes.

## 3. Deploy results without Blob access

### Commit the Windows results and use the existing deployment workflow

GitHub Releases are unavailable in the user's environment. The current path is
one explicitly reviewed JSON file committed to source. No release asset, Blob
upload or personal Azure Contributor role is required.

Use the file generated on the Windows laptop. From that repository's root:

```powershell
git switch main
git pull --ff-only origin main
New-Item -ItemType Directory -Force deploy | Out-Null
Copy-Item -LiteralPath "ml/artifacts/default-onset/frontend_predictions.json" -Destination "deploy/frontend_predictions.json"
git add -- deploy/frontend_predictions.json
git diff --cached --stat -- deploy/frontend_predictions.json
git commit -m "Update research predictions from Windows training" -- deploy/frontend_predictions.json
git push origin main
```

If the source file is missing, complete the local training/export step first.
If Git reports nothing to commit, that JSON is already up to date. Do not force
add `ml/artifacts/` or download folders. The allowed tracked file is
`deploy/frontend_predictions.json`; its contents follow repository visibility.

After CI passes, open Actions → **Build and deploy Python app to Azure Web App -
sovernriskAI** → Run workflow → main. No release tag is needed. The package builder
automatically validates the committed JSON and copies it into the application's
result path. The existing deployment identity releases the package.

A source push runs checks but does not deploy Azure automatically. The model,
map and country APIs read packaged results automatically after the manual
release. Repeat copy → commit → push → deploy whenever Windows predictions change.
The app does not train during startup and does not use a different machine's
results unless that file is deliberately committed.

### Alternatively, build and deploy the ZIP from the laptop

Reuse the `frontend_predictions.json` that training already produced. Build the
frontend and package that one validated result file with the application:

```powershell
Push-Location frontend
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m scripts.package_app_service `
  --predictions-file "ml/artifacts/default-onset/frontend_predictions.json"
```

This creates `dist/app-service.zip` with results at
`backend/app/data/frontend_predictions.json`. It excludes the training inputs,
model binaries and other generated files. The optional tracked JSON copy is described above; other generated files remain out of Git.

Deploy **this locally built ZIP** using your existing authorized App Service
deployment method. If your Azure CLI identity has App Service deployment access,
the manual release command is:

```powershell
az webapp deploy --resource-group wbg-poc-rg --name sovernriskAI --src-path "dist/app-service.zip" --type zip
```

This performs an App Service release. It requires your existing deployment
permission, with no Blob role assignment, SAS token, storage upload or additional
app setting. A GitHub build sees only committed files. Commit the reviewed JSON at the path
above, or deploy the ZIP you just built.

After release, open `/api/models/status` to verify `available`, then refresh the
dashboard. Each result update uses a newly built ZIP and an App Service release;
training can be reused when the existing result file is already correct.
Without an explicit flag, the packager uses `deploy/frontend_predictions.json`
when present. If neither source is supplied, the package has no result file.

Source order is an explicit `PREDICTIONS_FILE` override, the packaged file, then
`PREDICTIONS_BLOB_URL`, then SQL. Packaged results take precedence over an old
Blob URL, so a blocked Blob account does not affect this path. For a local
preview you may set `PREDICTIONS_FILE` to the generated JSON's absolute path.
An explicitly configured missing/invalid file reports unavailable and does not
silently switch stores. To return to Blob, deploy a ZIP without packaged results
and clear any explicit file override.

The remaining sections describe the optional Blob route. Skip to verification
after a successful ZIP deployment if you are using the packaged-file route.

## 4. Optional Blob route: inspect existing storage and access

The user confirmed `sovernriskai` is the data lake and `sovernriskaiv1` is Blob
storage. Use Blob account `sovernriskaiv1` for the prediction JSON and App Service
`sovernriskAI` in `wbg-poc-rg`. Select an existing private container, or create
one such as `vega-models` during manual setup. Verify the resource group for the
storage account. These discovery commands are read-only:

```powershell
az account show --output table
az storage container list --account-name sovernriskaiv1 --auth-mode login --output table
az webapp identity show --resource-group wbg-poc-rg --name sovernriskAI
```

The developer uploading files needs **Storage Blob Data Contributor**, and the
App Service managed identity needs **Storage Blob Data Reader**, scoped to the
chosen container. Existing storage networking must permit both callers. Keep
containers private. Use the existing Azure CLI login for uploading and managed
identity for serving. See Microsoft's [Blob Python authentication guide](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python).

If permissions are missing, the following are manual setup commands to review
and run with the subscription administrator. They change Azure access. Replace
the container placeholder first; no resources are created by the training code.

```powershell
$predictionContainer = "<existing-private-container>"
$storageId = az storage account list --query "[?name=='sovernriskaiv1'].id | [0]" --output tsv
$containerScope = "$storageId/blobServices/default/containers/$predictionContainer"
$developerId = az ad signed-in-user show --query id --output tsv
$appIdentity = az webapp identity show --resource-group wbg-poc-rg --name sovernriskAI --query principalId --output tsv
az role assignment create --assignee-object-id $developerId --assignee-principal-type User --role "Storage Blob Data Contributor" --scope $containerScope
az role assignment create --assignee-object-id $appIdentity --assignee-principal-type ServicePrincipal --role "Storage Blob Data Reader" --scope $containerScope
```

If no system-assigned App Service identity exists, have the administrator enable
it first, or adapt the configuration/roles to the existing user-assigned identity.
Role propagation can take time. Resolve private DNS/VNet access through the
existing network configuration.

## 5. Optional Blob route: publish result data from the laptop

This explicit command writes Azure Blob data. Run it after reviewing the model
metrics and selecting the container. It uploads an archived version followed by
the current JSON bundle. Model binaries are not uploaded by this command.

```powershell
$predictionBlobUrl = "https://sovernriskaiv1.blob.core.windows.net/$predictionContainer/predictions/current.json"
.\.venv\Scripts\python.exe -m ml.prediction_bundle publish `
  --file "ml/artifacts/default-onset/frontend_predictions.json" `
  --blob-url $predictionBlobUrl
```

Use a single publisher at a time. Each JSON blob replacement is complete, so
readers never consume a partly written file. Archived versions support rollback.
An upload failure before current replacement leaves the last current file intact.
The serving cache refreshes within one minute. A failed refresh reports results
unavailable; it does not silently label an old bundle current.

## 6. Optional Blob route: manually activate the App Service

The existing hosted app must have this feature's code before it can read Blob
results. Source pushes do not deploy. Review and perform this activation
separately; these commands change/release the Azure app.

Build an application ZIP from the reviewed source using native tools:

```powershell
Push-Location frontend
npm ci
npm test
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m scripts.package_app_service
```

After confirming managed-identity access and publishing a valid bundle, configure
the result URL and manually release the ZIP. The setting change restarts the app.
Keep the existing Python runtime, startup command and other application settings.

```powershell
az webapp config appsettings set --resource-group wbg-poc-rg --name sovernriskAI --settings "PREDICTIONS_BLOB_URL=$predictionBlobUrl" --output none
az webapp deploy --resource-group wbg-poc-rg --name sovernriskAI --src-path "dist/app-service.zip" --type zip
```

This package excludes ML dependencies and model binaries. It serves precomputed
JSON results. The runtime needs the ordinary requirements, which now include
Azure Identity and Blob SDKs. Retain the app's existing build-on-deployment setup.

## 7. Verify hosted results

```powershell
$appUrl = "https://sovernriskai-c8dbcqe6edapeuae.eastus2-01.azurewebsites.net"
Invoke-RestMethod "$appUrl/api/models/status"
Invoke-RestMethod "$appUrl/api/data/map?indicator=default-risk&year=2025"
Invoke-RestMethod "$appUrl/api/countries/IND/prediction"
```

An eligible country returns a probability between 0 and 1 plus model/snapshot,
outcome year and feature year. The UI displays the model estimate as a percentage with its research kind
and outcome year. Latest catalog rows with insufficient inputs return a null score and show
Insufficient data. Legacy historical bundles return 404 for an absent test row. A Blob permissions/configuration/validation failure returns
503. GDP growth continues through the World Bank API. The existing `/health`
check still covers SQL, since the rest of that storage migration remains pending.

For the Blob route, repeat training and the explicit data-publish command.
Once this code/configuration is active, updating results needs no code release.
To roll back results, publish a previously reviewed archived JSON file to the
same current URL. Clear `PREDICTIONS_BLOB_URL` to return to the existing SQL
prediction adapter.
