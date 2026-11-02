"""Tests everything except Prophet/MLflow by using the seasonal-naive stand-in as the 'forecast'."""
import sys, types
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
for m in ["mlflow", "prophet", "joblib"]:          # stubs so forecast_mlflow imports
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["prophet"].Prophet = object
sys.modules["joblib"].Parallel = sys.modules["joblib"].delayed = None
import forecast_mlflow as fm

sales = pd.read_csv(ROOT / "data/sales.csv", parse_dates=["ds"])
fcs, accs, bts = [], [], []
for (r, s), g in sales.groupby(["region", "sku"]):
    g = g.sort_values("ds").reset_index(drop=True)
    _, m, bt = fm.backtest_one((r, s), g, {}, fm.naive_forecast)
    accs.append((r, s, m)); bts.append(bt.assign(region=r, sku=s))
    f = fm.naive_forecast(g, {}, 13).assign(region=r, sku=s)
    fcs.append(f.rename(columns={"yhat_lower": "yhat_lo", "yhat_upper": "yhat_hi"}))
(ROOT / "outputs").mkdir(exist_ok=True)
pd.concat(fcs).to_csv(ROOT / "outputs/forecast.csv", index=False)
pd.concat(bts).to_csv(ROOT / "outputs/backtest.csv", index=False)
pd.DataFrame(accs, columns=["region", "sku", "mape"]).to_csv(ROOT / "outputs/accuracy.csv", index=False)
print("seasonal-naive mean MAPE:", round(np.mean([a[2] for a in accs]), 2))
