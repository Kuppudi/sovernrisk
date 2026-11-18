# Reviewed prediction results

Copy the result generated on the Windows laptop to
`deploy/frontend_predictions.json`, then commit and push that one JSON file.
The package builder automatically validates it and includes it inside the app
at `backend/app/data/frontend_predictions.json`. GitHub Releases and Blob upload
permissions are unnecessary for this delivery path.

From the repository root in PowerShell, after updating main:

```powershell
New-Item -ItemType Directory -Force deploy | Out-Null
Copy-Item -LiteralPath "ml/artifacts/default-onset/frontend_predictions.json" -Destination "deploy/frontend_predictions.json"
git add -- deploy/frontend_predictions.json
git diff --cached --stat -- deploy/frontend_predictions.json
git commit -m "Update research predictions from Windows training" -- deploy/frontend_predictions.json
git push origin main
```

Then use the existing manual App Service deployment workflow on main. A source
push runs CI and does not deploy Azure automatically. Updating this JSON and
deploying the new commit updates the displayed research results.

This tracked JSON is the user's explicit exception to the generated-output
exclusion policy. Keep raw datasets, label downloads, metrics exports, model
binaries, credentials and other local files excluded. The JSON follows repository
visibility. Missing eligible-country results remain unavailable, and the UI keeps
the research-kind label and outcome year. Rerun `python -m ml.run_training`
for schema-2 latest-data estimates before copying; this is separate from the
legacy held-out historical export.
