# Local ML training and hosted prediction results

Run training on the Windows laptop. Upload the result JSON to existing private
Blob Storage, then let the existing App Service read it for the map and country
card. Training needs neither Docker nor a database nor an Azure ML compute job.
The app's other stored-data/report paths currently retain their SQL dependency.

The current model produces **historical held-out research probabilities** for
default onset, using nine economic/debt features and documented default labels.
The default test window is 2019–2025. These results do not establish a current
forecast. The UI keeps the research label and outcome year. Countries without
eligible predictions remain unavailable. AI / RAG stays Coming soon.

## 1. Get the source and install on Windows

From the repository root in the VS Code PowerShell terminal, fetch and check out
the delivery branch while preserving existing work. After it is merged, use main.

```powershell
git fetch origin
git switch feature/local-ml-predictions
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock -e ".[ml]"
```

## 2. Download and train on the laptop

```powershell
.\.venv\Scripts\python.exe -m ml.run_training --download-inputs
```

This downloads the global 1990–2025 WDI panel and official BoC–BoE workbook,
then runs training, validation and historical testing on the laptop CPU. It
does not submit a cloud job, write SQL or upload results. Allow time for provider
downloads. The frontend's economic display window remains 2015–2025.

Outputs under ignored `ml/artifacts/default-onset/` include `metrics.json`,
`research_model.joblib`, `historical_test_predictions.csv` and
`frontend_predictions.json`. Keep source datasets and outputs out of Git.

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

To export an already completed run without retraining:

```powershell
.\.venv\Scripts\python.exe -m ml.prediction_bundle export `
  --snapshot "data/raw/global-wdi-1990-2025.json" `
  --output "ml/artifacts/default-onset"
```

The export verifies the snapshot version, feature schema, held-out year range,
probability bounds, country coverage and unique country/year rows. It includes
all snapshot countries, with scores only for eligible test rows. The current
card uses the latest outcome year in the bundle; missing countries do not fall
back to older years.

## 3. Inspect existing storage and access

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

## 4. Publish result data from the laptop

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

## 5. Manually activate the code in the existing App Service

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

## 6. Verify hosted results

```powershell
$appUrl = "https://sovernriskai-c8dbcqe6edapeuae.eastus2-01.azurewebsites.net"
Invoke-RestMethod "$appUrl/api/models/status"
Invoke-RestMethod "$appUrl/api/data/map?indicator=default-risk&year=2025"
Invoke-RestMethod "$appUrl/api/countries/IND/prediction"
```

An eligible country returns a probability between 0 and 1 plus model/snapshot,
outcome year and feature year. The UI displays the probability as a percentage
and marks it Historical research. Missing eligible coverage returns 404 and
appears Unavailable. A Blob permissions/configuration/validation failure returns
503. GDP growth continues through the World Bank API. The existing `/health`
check still covers SQL, since the rest of that storage migration remains pending.

For later model runs, repeat training and the explicit data-publish command.
Once this code/configuration is active, updating results needs no code release.
To roll back results, publish a previously reviewed archived JSON file to the
same current URL. Clear `PREDICTIONS_BLOB_URL` to return to the existing SQL
prediction adapter.
