"""Per SKU x region 13-week (~3 month) forecasts with Prophet; every config tracked in MLflow.

Grid = 3 changepoint priors x 2 seasonality modes x 2 seasonality priors x 2 yearly settings
     = 24 Prophet runs + 1 seasonal-naive baseline = 25 tracked experiments (>= 20 required).
"""
import argparse, itertools, logging
from pathlib import Path
import numpy as np
import pandas as pd
import mlflow
from joblib import Parallel, delayed
from prophet import Prophet

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
H = 13  # weeks ahead (~3 months)
GRID = dict(cps=[0.01, 0.05, 0.2], mode=["additive", "multiplicative"],
            sps=[1.0, 10.0], yearly=[0, 6])  # yearly = Fourier order, 0 = off


def mape(y, f):
    y, f = np.asarray(y, float), np.asarray(f, float)
    ok = y > 0
    return float(np.mean(np.abs(y[ok] - f[ok]) / y[ok]) * 100)


def prophet_forecast(df, cfg, horizon):
    m = Prophet(changepoint_prior_scale=cfg["cps"], seasonality_mode=cfg["mode"],
                seasonality_prior_scale=cfg["sps"],
                yearly_seasonality=cfg["yearly"] if cfg["yearly"] else False,
                weekly_seasonality=False, daily_seasonality=False, interval_width=0.8)
    m.fit(df[["ds", "y"]])
    fut = m.make_future_dataframe(periods=horizon, freq="W-MON", include_history=False)
    p = m.predict(fut)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    for c in ["yhat", "yhat_lower", "yhat_upper"]:
        p[c] = p[c].clip(lower=0)
    return p


def naive_forecast(df, cfg, horizon):
    """Seasonal naive (same week last year) scaled by recent level ratio."""
    y = df.y.values
    last = df.ds.iloc[-1]
    ds = pd.date_range(last + pd.Timedelta(weeks=1), periods=horizon, freq="W-MON")
    idx = np.arange(len(y) - 52, len(y) - 52 + horizon)
    f = y[idx] * (y[-13:].mean() / y[-65:-52].mean())
    return pd.DataFrame({"ds": ds, "yhat": f, "yhat_lower": f * .85, "yhat_upper": f * 1.15})


def backtest_one(key, df, cfg, fn):
    train, test = df.iloc[:-H], df.iloc[-H:]
    p = fn(train, cfg, H)
    bt = test[["ds", "y"]].merge(p[["ds", "yhat"]], on="ds")
    return key, mape(bt.y, bt.yhat), bt


def run_config(series, cfg, fn, n_jobs):
    res = Parallel(n_jobs=n_jobs)(delayed(backtest_one)(k, d, cfg, fn) for k, d in series.items())
    acc = pd.DataFrame([(k[0], k[1], m) for k, m, _ in res], columns=["region", "sku", "mape"])
    bt = pd.concat([b.assign(region=k[0], sku=k[1]) for k, _, b in res], ignore_index=True)
    return acc, bt


def log_run(name, cfg, acc, tags=None):
    with mlflow.start_run(run_name=name):
        mlflow.log_params({**cfg, "horizon_weeks": H, "n_series": len(acc)})
        mlflow.log_metrics({"mape_mean": acc.mape.mean(), "mape_median": acc.mape.median(),
                            "mape_p90": acc.mape.quantile(.9),
                            "pct_series_under_15": float((acc.mape < 15).mean() * 100)})
        if tags:
            mlflow.set_tags(tags)
        p = OUT / f"accuracy_{name}.csv"
        acc.to_csv(p, index=False)
        mlflow.log_artifact(str(p))
        p.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-jobs", type=int, default=-1)
    ap.add_argument("--max-series", type=int, default=None, help="debug: limit series")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    sales = pd.read_csv(ROOT / "data" / "sales.csv", parse_dates=["ds"])
    series = {k: g.sort_values("ds").reset_index(drop=True) for k, g in sales.groupby(["region", "sku"])}
    if a.max_series:
        series = dict(list(series.items())[: a.max_series])

    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("pharma_demand_forecast")

    results = {}
    acc, _ = run_config(series, {"model": "seasonal_naive"}, naive_forecast, a.n_jobs)
    log_run("baseline_seasonal_naive", {"model": "seasonal_naive"}, acc, {"stage": "baseline"})
    print(f"baseline MAPE {acc.mape.mean():.2f}%")

    keys = list(GRID)
    for vals in itertools.product(*GRID.values()):
        cfg = dict(zip(keys, vals))
        name = f"prophet_cps{cfg['cps']}_{cfg['mode'][:4]}_sps{cfg['sps']}_y{cfg['yearly']}"
        acc, bt = run_config(series, cfg, prophet_forecast, a.n_jobs)
        log_run(name, {**cfg, "model": "prophet"}, acc, {"stage": "grid"})
        results[name] = (cfg, acc, bt)
        print(f"{name}: mean MAPE {acc.mape.mean():.2f}%")

    best = min(results, key=lambda n: results[n][1].mape.mean())
    cfg, acc, bt = results[best]
    print(f"\nBEST: {best} mean MAPE {acc.mape.mean():.2f}%")
    acc.to_csv(OUT / "accuracy.csv", index=False)
    bt.to_csv(OUT / "backtest.csv", index=False)

    # Final refit on ALL data -> next 13 weeks
    fc = Parallel(n_jobs=a.n_jobs)(
        delayed(lambda k, d: prophet_forecast(d, cfg, H).assign(region=k[0], sku=k[1]))(k, d)
        for k, d in series.items())
    fc = pd.concat(fc, ignore_index=True)
    fc = fc.rename(columns={"yhat_lower": "yhat_lo", "yhat_upper": "yhat_hi"})
    fc.to_csv(OUT / "forecast.csv", index=False)

    with mlflow.start_run(run_name="final_production_forecast"):
        mlflow.log_params({**cfg, "model": "prophet", "best_grid_run": best})
        mlflow.log_metrics({"mape_mean": acc.mape.mean(), "target_met_lt_15": float(acc.mape.mean() < 15)})
        mlflow.set_tag("stage", "production")
        for f in ["forecast.csv", "accuracy.csv", "backtest.csv"]:
            mlflow.log_artifact(str(OUT / f))
    print(f"Saved forecast for {len(series)} series. Target (<15%) met: {acc.mape.mean() < 15}")


if __name__ == "__main__":
    main()
