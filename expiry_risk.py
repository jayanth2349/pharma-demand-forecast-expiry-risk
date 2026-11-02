"""Flag batches likely to expire unsold, using forecast demand and FIFO (earliest-expiry-first) depletion."""
import os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
MAX_EXTEND_WEEKS = 80


def tier(days, pct):
    if pct <= 0:
        return "None"
    if days <= 90 and pct >= 0.20:
        return "High"
    if days <= 180 and pct >= 0.10:
        return "Medium"
    if days <= 365:
        return "Low"
    return "None"


def simulate(fc, batches, as_of):
    """fc: one series' forecast (ds, yhat). batches: that series' batches. Returns batches + at_risk_units."""
    fc = fc.sort_values("ds")
    dates, demand = list(fc.ds), list(fc.yhat)
    rate = float(fc.yhat.tail(4).mean())  # beyond horizon: hold recent forecast level
    max_exp = batches.expiry_date.max()
    while dates[-1] < max_exp and len(dates) < len(fc) + MAX_EXTEND_WEEKS:
        dates.append(dates[-1] + pd.Timedelta(weeks=1))
        demand.append(rate)

    b = batches.sort_values("expiry_date").reset_index(drop=True)
    stock = b.stock_units.astype(float).tolist()
    exp = list(b.expiry_date)
    lost = [0.0] * len(b)
    gone = [False] * len(b)
    for d, q in zip(dates, demand):
        for i in range(len(b)):  # write off anything expired before this week starts
            if not gone[i] and exp[i] <= d:
                lost[i], stock[i], gone[i] = stock[i], 0.0, True
        for i in range(len(b)):  # FIFO consumption
            if q <= 0:
                break
            take = min(q, stock[i])
            stock[i] -= take
            q -= take
    for i in range(len(b)):  # anything left after the simulated window also counts as at risk
        if not gone[i]:
            lost[i] = stock[i]
    b["at_risk_units"] = [round(x) for x in lost]
    return b


def flag(forecast, batches, as_of):
    parts = []
    for (region, sku), bg in batches.groupby(["region", "sku"]):
        fg = forecast[(forecast.region == region) & (forecast.sku == sku)]
        if fg.empty:
            continue
        parts.append(simulate(fg, bg, as_of))
    r = pd.concat(parts, ignore_index=True)
    r["days_to_expiry"] = (r.expiry_date - as_of).dt.days
    r["at_risk_pct"] = (r.at_risk_units / r.stock_units).round(3)
    r["value_at_risk"] = (r.at_risk_units * r.unit_cost).round(2)
    r["risk_tier"] = [tier(d, p) for d, p in zip(r.days_to_expiry, r.at_risk_pct)]
    order = {"High": 0, "Medium": 1, "Low": 2, "None": 3}
    return r.sort_values(by=["risk_tier", "value_at_risk"], key=lambda c: c.map(order) if c.name == "risk_tier" else -c)


def notify(alerts):
    """Print alerts; also post a summary to Slack/Teams if SLACK_WEBHOOK_URL is set."""
    hi = alerts[alerts.risk_tier == "High"]
    msg = (f"Expiry risk: {len(hi)} HIGH, {(alerts.risk_tier=='Medium').sum()} MEDIUM batches. "
           f"Value at risk (High): {hi.value_at_risk.sum():,.0f}")
    print(msg)
    url = os.getenv("SLACK_WEBHOOK_URL")
    if url:
        import requests
        requests.post(url, json={"text": msg}, timeout=10)


def main(as_of=pd.Timestamp("2026-11-02")):
    fc = pd.read_csv(OUT / "forecast.csv", parse_dates=["ds"])
    batches = pd.read_csv(ROOT / "data" / "batches.csv", parse_dates=["expiry_date"])
    res = flag(fc, batches, as_of)
    res.to_csv(OUT / "expiry_all_batches.csv", index=False)
    alerts = res[res.risk_tier != "None"]
    alerts.to_csv(OUT / "expiry_alerts.csv", index=False)
    notify(alerts)
    return alerts


if __name__ == "__main__":
    main()
