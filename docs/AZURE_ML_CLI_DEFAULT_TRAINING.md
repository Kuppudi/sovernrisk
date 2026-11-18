# Azure ML CLI default training workflow

This runbook executes default-onset training as an Azure ML command job with no
local input data files required.

The job itself downloads:

- World Bank global WDI archives for 1990-2025
- BoC-BoE 2026 default workbook

Then it runs `ml.default_training` and writes artifacts.

## 1) Prerequisites

- Azure CLI (`az`) installed and logged in.
- `az ml` extension installed.
- Access to resource group `wbg-poc-rg` and workspace `sovernriskAI-diviml`.
- A compute target in AML named `cpu-cluster` (or update the YAML).

Install or update ML extension:

```powershell
az extension add --name ml --upgrade
```

Select subscription:

```powershell
az account set --subscription 97c7b242-6f62-4912-b4e3-373a6e52ad78
```

## 2) Submit the training job

From repository root:

```powershell
az ml job create `
  --resource-group wbg-poc-rg `
  --workspace-name sovernriskAI-diviml `
  --file infrastructure/azure/ml/default_training_job.yml `
  --stream
```

This job runs:

- `python -m pip install -e ".[ml]"`
- `python -m ml.azureml_run_default_training ...`

## 3) Download artifacts

After completion, get the latest job name:

```powershell
$jobName = az ml job list `
  --resource-group wbg-poc-rg `
  --workspace-name sovernriskAI-diviml `
  --query "[?contains(display_name, 'vega-default-onset-training')] | sort_by(@, &creation_context.created_at)[-1].name" `
  --output tsv
$jobName
```

Download all outputs:

```powershell
az ml job download `
  --resource-group wbg-poc-rg `
  --workspace-name sovernriskAI-diviml `
  --name $jobName `
  --download-path ./aml-job-output
```

Expected artifacts:

- `metrics.json`
- `research_model.joblib`
- `historical_test_predictions.csv`

## 4) Optional: change compute or output path

Update these in `infrastructure/azure/ml/default_training_job.yml`:

- `compute: azureml:cpu-cluster`
- `outputs.trained_artifacts.path`

## Notes

- This path is cloud-only for data extraction and training inputs.
- It does not make frontend debt scores live. Serving requires backend inference
  wiring and frontend integration to prediction APIs.
