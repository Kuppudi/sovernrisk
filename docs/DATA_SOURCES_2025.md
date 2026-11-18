# 2025 observations, coverage and model accuracy

World Bank WDI released 2025 national-accounts and population data in its July
2026 update. Refresh the official archive before assuming 2025 GDP is missing.
Different indicators and economies still have different reporting coverage.
[World Bank release notes](https://datatopics.worldbank.org/world-development-indicators/release-note/jul-2026.html).

The IMF October 2026 WEO dataset is an alternative for macroeconomic indicators
such as growth, inflation and fiscal statistics. Some data remain preliminary,
estimated or projected. The WEO documentation explains the distinctions and
why values can differ from other statistical sources.
[WEO dataset](https://www.imf.org/external/datamapper/datasets/WEO),
[WEO data-status and revision FAQ](https://data.imf.org/en/Datasets/WEO/Frequently-Asked-Questions).

An additional source cannot guarantee forecast accuracy. Before using a value
as a model feature, preserve provider, edition/revision, units, reference period,
retrieval time and actual/estimate/projection status. Match definitions, then
evaluate the same provider/fallback policy across historical train/validation/test
periods. Filling only the latest inference year with a new provider can create
a distribution change that the historical evaluation did not test.

In particular, IMF general-government debt as percent of GDP is a different
feature from WDI external debt as percent of GNI. End-period and annual-average
inflation also differ. Those values cannot silently replace one another just
because their labels contain debt or inflation. Current IMF fiscal ingestion
preserves its own codes and units separately.

This feature does not automatically overwrite WDI with IMF values. It expands
scoring beyond the labeled test cohort, uses documented bounded historical
carry-forward, and exposes remaining coverage gaps. The four-feature minimum
prevents unsupported scores for economies with too little recent input data.
The default scope includes territories/economies as well as sovereign countries;
sovereign-default label coverage and applicability are not universal.

As of the existing verification snapshot, 194 of 217 economies meet the minimum
for 2025 reference inputs after at most two years of carry-forward. The remaining
23 require more suitable data. All 217 receive coverage rows; a null score is
not replaced with a zero or an all-median default probability.
