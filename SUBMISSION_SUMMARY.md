**Objective.** Forecast 3-month (13-week) demand per SKU per region and flag batches likely to expire unsold, with MLflow experiment tracking, a regional dashboard and weekly automated reporting.

**Data.** The three provided packs (healthcare appointments, patient satisfaction, resource utilisation) contain no drug-level data, so I simulated weekly sales (8 SKUs x 4 Sunrise hospitals x 104 weeks) and batch inventory. Seasonality was derived from 2025 appointment volumes, SKU mix from specialty share, and regional scale from bed occupancy. Replacing the two input CSVs with real data requires no code change.

**Methodology.** Facebook Prophet per SKU-region series; time-based holdout of the last 13 weeks; MAPE as the metric. 24 hyper-parameter configurations (changepoint prior x seasonality mode x seasonality prior x yearly seasonality) plus a seasonal-naive baseline = 25 MLflow runs. Best config is refit on all data. Expiry risk: forecast demand depletes batches earliest-expiry-first; units left at expiry are "at risk" and tiered High/Medium/Low.

**Assumptions.** Synthetic demand (noise set by generator, so accuracy is indicative of pipeline validity only); weekly grain; demand beyond horizon held at recent forecast level; tier thresholds in README.

**Key findings.** [FILL AFTER YOU RUN: best config = ___; mean MAPE = ___% (target <15%); ___% of series under 15%; baseline MAPE = ___%; ___ High / ___ Medium batches, value at risk = ___.]

**Recommendations / limitations.** Redistribute or return High-tier batches between regions, tighten reorder quantities for SKUs with chronic overstock. Validate on real sales; add promotions/epidemic regressors; MAPE is unstable for low-volume SKUs (consider WAPE).

**Deliverables.** Code (zip), MLflow runs (mlflow.db), Streamlit dashboard, weekly report workflow.
