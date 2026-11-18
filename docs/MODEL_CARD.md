# Model card · production models unavailable

An offline sovereign default-onset experiment is implemented in
`ml/default_training.py` and `notebooks/default_training.ipynb`. It is
retrospective research. Production validation and live forecasting remain
incomplete. The optional Blob results adapter can serve held-out historical probabilities, explicitly
marked as research with their outcome/feature years. It serves JSON outputs,
not serialized model artifacts. No SHAP explanations are implemented.

Intended use: sovereign credit and loan-repayment risk analysis for development-finance lenders, other financial institutions, and insurers. This is the product focus, not a claim that a repayment/default model has already been trained. A repayment outcome, time horizon, and authorized repayment/default history must be defined before training that model. A rating downgrade is a different event and must not be presented as loan non-repayment.

## Model A · Sovereign credit risk

The offline research target is the transition from zero to positive conventional
sovereign debt in default between consecutive years in the 2026 BoC–BoE
workbook. The experiment models eligible issuers with available WDI features
and explicit label coverage. Loan-level repayment performance requires a
loan-level outcome dataset.

## Model B · Twelve-month downgrade probability

Requires authorized rating event history, agency, issuer/instrument scope, currency basis, observation eligibility, censoring rules, event definition, and a precise twelve-month horizon. No labels or licensed rating history are supplied. An absent event record is not automatically a negative label.

## Required before training and serving

1. Confirm target, intended use, coverage, redistribution rights, and label completeness.
2. Establish historically known-at-time feature vintages. Current WDI downloads and response revision dates cannot establish original availability.
3. Define an immutable feature schema, units, missingness/lag policies, scaling, and reproducible snapshot references.
4. Train offline using chronological partitions and walk-forward backtests. Compare logistic regression with boosting; address country effects and imbalance without temporal leakage.
5. Report ROC-AUC, PR-AUC, precision/recall, thresholded confusion matrices, Brier score, calibration curves, baseline comparisons, and coverage/subgroup limitations. Do not fit calibration on the test period.
6. Store target/license definition, dataset snapshots, preprocessing, metrics, dependency versions, schema, artifact integrity, and reviewed limitations. Load only trusted artifacts, never user uploads.
7. Validate lightweight offline-loaded inference, invalid/stale/missing feature rejection, calibrated probabilities, and faithful attributions.

Optional dependencies are in `.[ml]`. The offline experiment uses
chronological train, validation, and test splits. Production validation
requires historical feature vintages, calibration, and artifact checks.
