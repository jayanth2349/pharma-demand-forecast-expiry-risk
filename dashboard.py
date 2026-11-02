"""Regional drill-down dashboard.  Run:  streamlit run dashboard.py"""
import sqlite3
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DB = Path(__file__).parent / "pharma.db"
st.set_page_config(page_title="Pharma Demand & Expiry", layout="wide")


@st.cache_data
def q(sql, params=()):
    con = sqlite3.connect(DB)
    df = pd.read_sql(sql, con, params=params)
    con.close()
    return df


st.title("Drug Demand Forecast & Expiry Risk")
regions = q("SELECT DISTINCT region FROM sales ORDER BY 1").region.tolist()
region = st.sidebar.selectbox("Region", regions)
skus = q("SELECT DISTINCT sku FROM sales WHERE region=? ORDER BY 1", (region,)).sku.tolist()
sku = st.sidebar.selectbox("SKU", skus)

acc = q("SELECT * FROM accuracy WHERE region=?", (region,))
c1, c2, c3 = st.columns(3)
c1.metric("Region mean MAPE", f"{acc.mape.mean():.1f}%")
c2.metric(f"{sku} MAPE", f"{acc[acc.sku == sku].mape.iloc[0]:.1f}%")
alerts = q("SELECT * FROM expiry_alerts WHERE region=?", (region,))
c3.metric("High-risk batches", int((alerts.risk_tier == 'High').sum()))

hist = q("SELECT ds, y FROM sales WHERE region=? AND sku=? ORDER BY ds", (region, sku))
fc = q("SELECT ds, yhat, yhat_lo, yhat_hi FROM forecast WHERE region=? AND sku=? ORDER BY ds", (region, sku))
fig = go.Figure()
fig.add_scatter(x=hist.ds, y=hist.y, name="Actual")
fig.add_scatter(x=fc.ds, y=fc.yhat, name="Forecast", line=dict(dash="dash"))
fig.add_scatter(x=fc.ds, y=fc.yhat_hi, line=dict(width=0), showlegend=False)
fig.add_scatter(x=fc.ds, y=fc.yhat_lo, fill="tonexty", line=dict(width=0), name="80% interval")
fig.update_layout(title=f"{sku} - {region}: weekly units", height=380)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Region comparison: next-13-week forecast by SKU")
st.bar_chart(q("SELECT sku, ROUND(SUM(yhat)) AS units FROM forecast WHERE region=? GROUP BY sku", (region,)).set_index("sku"))

st.subheader("Expiry risk alerts")
tiers = st.multiselect("Tiers", ["High", "Medium", "Low"], default=["High", "Medium"])
st.dataframe(alerts[alerts.risk_tier.isin(tiers)][
    ["batch_id", "sku_name", "expiry_date", "days_to_expiry", "stock_units",
     "at_risk_units", "at_risk_pct", "value_at_risk", "risk_tier"]], use_container_width=True)
