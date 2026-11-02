# Drug Demand Forecasting & Expiry Risk System

## Run (Python 3.10+)
```bash
pip install -r requirements.txt
python run_pipeline.py          # data -> 25 MLflow runs -> forecast -> expiry alerts -> SQLite -> weekly report
mlflow ui --backend-store-uri sqlite:///mlflow.db     # view the experiments (http://127.0.0.1:5000)
streamlit run dashboard.py      # regional drill-down dashboard
```
Training fits 24 Prophet configs x 32 series (~770 fits); expect 10-20 min. Use `python forecast_mlflow.py --max-series 4` to debug.

## Files
| File | Purpose |
|---|---|
| generate_data.py | Synthetic sales + batch stock, anchored to the 3 provided CSVs (they contain no drug data) |
| forecast_mlflow.py | Prophet per SKU x region, 13-week holdout MAPE, 24 grid runs + baseline logged to MLflow |
| expiry_risk.py | FIFO depletion with forecast demand -> High/Medium/Low expiry alerts (+ optional Slack webhook) |
| run_pipeline.py | Orchestrator; loads everything into SQLite (pharma.db) |
| queries.sql, weekly_report.py | SQL rollups + weekly Markdown report |
| dashboard.py | Streamlit dashboard (region/SKU filters, forecast bands, alerts) |
| .github/workflows/weekly.yml | Monday 03:00 UTC automation (or cron: `0 3 * * 1`) |

## Key assumptions
- Provided CSVs hold no SKU/expiry data; sales and inventory are simulated. Seasonality comes from appointment volume,
  SKU mix from specialty share, regional scale from bed occupancy. Because noise is set by the generator, MAPE here
  validates the pipeline, not real-world accuracy. Swap data/sales.csv and data/batches.csv for real data (same columns).
- Regions = 4 Sunrise hospitals; weekly grain, 104 weeks; holdout = last 13 weeks.
- Expiry: FIFO consumption; beyond the 13-week forecast, demand is held at the last-4-week forecast average.
  Tiers: High = <=90 days & >=20% at risk; Medium = <=180 days & >=10%; Low = <=365 days & >0.
