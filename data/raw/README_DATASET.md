# US Climate Disaster & Flood Insurance Risk

This release combines redacted NFIP claim aggregates, NOAA Storm Events, and FEMA disaster declarations at a county-year grain. It contains 83,804 county-year rows covering 2000–2026.

## Interpretation

`composite_risk_score` is a transparent weighted percentile index for exploration. It is not a premium indication, underwriting decision, catastrophe model, or causal estimate. NFIP coverage totals are coverage represented by claims, not all active policy exposure. NOAA damages and NFIP payments measure different concepts and should not be expected to reconcile.

All monetary values are nominal U.S. dollars. Source limitations and extraction hashes are recorded in `source_manifest.json`; validation results are in `quality_report.json`.
