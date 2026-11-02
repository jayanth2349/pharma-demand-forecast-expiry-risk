"""End-to-end: data -> forecast (MLflow) -> expiry alerts -> SQLite -> weekly report."""
import argparse, sqlite3, subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent


def load_sqlite():
    con = sqlite3.connect(ROOT / "pharma.db")
    for name, path in [("sales", "data/sales.csv"), ("batches", "data/batches.csv"),
                       ("forecast", "outputs/forecast.csv"), ("backtest", "outputs/backtest.csv"),
                       ("accuracy", "outputs/accuracy.csv"), ("expiry_alerts", "outputs/expiry_alerts.csv"),
                       ("expiry_all_batches", "outputs/expiry_all_batches.csv")]:
        pd.read_csv(ROOT / path).to_sql(name, con, if_exists="replace", index=False)
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-train", action="store_true", help="reuse existing forecast.csv")
    ap.add_argument("--regen-data", action="store_true")
    a = ap.parse_args()
    py = sys.executable
    if a.regen_data or not (ROOT / "data/sales.csv").exists():
        subprocess.check_call([py, str(ROOT / "generate_data.py")])
    if not a.skip_train:
        subprocess.check_call([py, str(ROOT / "forecast_mlflow.py")])
    import expiry_risk
    expiry_risk.main()
    load_sqlite()
    import weekly_report
    weekly_report.main()
