"""Generate the weekly Markdown report (run by cron / GitHub Actions every Monday)."""
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent


def main():
    con = sqlite3.connect(ROOT / "pharma.db")
    q = lambda s: pd.read_sql(s, con)
    acc = q("SELECT * FROM accuracy")
    reg = q("""SELECT f.region, ROUND(SUM(f.yhat)) AS forecast_13w,
               (SELECT SUM(s.y) FROM sales s WHERE s.region=f.region
                  AND s.ds >= (SELECT DATE(MAX(ds),'-84 day') FROM sales)) AS actual_prev_13w
               FROM forecast f GROUP BY f.region""")
    reg["change_pct"] = ((reg.forecast_13w / reg.actual_prev_13w - 1) * 100).round(1)
    tiers = q("""SELECT risk_tier, COUNT(*) batches, SUM(at_risk_units) units,
                 ROUND(SUM(value_at_risk),2) value_at_risk FROM expiry_alerts GROUP BY risk_tier""")
    top = q("""SELECT region, sku_name, batch_id, expiry_date, days_to_expiry, stock_units,
               at_risk_units, value_at_risk, risk_tier FROM expiry_alerts
               WHERE risk_tier IN ('High','Medium') ORDER BY value_at_risk DESC LIMIT 10""")
    date = q("SELECT MIN(ds) d FROM forecast").d[0]
    con.close()

    md = [f"# Weekly Pharma Demand & Expiry Report - week of {date}", "",
          "## Forecast accuracy (13-week holdout backtest)",
          f"- Mean MAPE: **{acc.mape.mean():.1f}%** (target < 15%) - "
          f"{'MET' if acc.mape.mean() < 15 else 'NOT MET'}",
          f"- Series under 15%: {(acc.mape < 15).mean() * 100:.0f}% of {len(acc)}",
          "", "## Regional demand outlook (next 13 weeks vs previous 13)", reg.to_markdown(index=False),
          "", "## Expiry risk summary", tiers.to_markdown(index=False),
          "", "## Top 10 batches to act on (redistribute / discount / return)", top.to_markdown(index=False), ""]
    out = ROOT / "outputs" / f"weekly_report_{date}.md"
    out.write_text("\n".join(md))
    print("wrote", out)


if __name__ == "__main__":
    main()
