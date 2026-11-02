"""Build a synthetic drug-sales + batch-inventory dataset anchored to the provided CSVs.

The provided packs contain NO drug/SKU/expiry data, so we simulate it:
  * seasonality  <- monthly appointment volume in da_healthcare_appointments.csv
  * SKU mix      <- specialty share of appointments (each SKU maps to a specialty)
  * region scale <- mean bed occupancy per hospital in sunrise_resource_utilisation.csv
Regions = the four Sunrise hospitals. Weekly demand, 104 weeks, 8 SKUs x 4 regions.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

# sku: (name, specialty, unit_cost, seasonal_peak_month)
SKUS = {
    "PARA500": ("Paracetamol 500mg", "General Medicine", 0.8, None),
    "AMLO5": ("Amlodipine 5mg", "Cardiology", 1.5, None),
    "ATOR10": ("Atorvastatin 10mg", "Cardiology", 2.2, None),
    "AMOX500": ("Amoxicillin 500mg", "ENT", 3.0, 1),
    "CETI10": ("Cetirizine 10mg", "Dermatology", 1.0, 4),
    "IBU400": ("Ibuprofen 400mg", "Orthopedics", 1.2, None),
    "TIMO_ED": ("Timolol eye drops", "Ophthalmology", 45.0, None),
    "OMEP20": ("Omeprazole 20mg", "General Medicine", 1.8, None),
}
N_WEEKS = 104
AS_OF = pd.Timestamp("2026-11-02")  # Monday; first forecast week


def anchors():
    appt = pd.read_csv(RAW / "da_healthcare_appointments.csv", parse_dates=["appointment_date"])
    appt = appt[appt.appointment_date.dt.year == 2025]  # only full year
    m = appt.groupby(appt.appointment_date.dt.month).size()
    month_idx = (m / m.mean()).reindex(range(1, 13)).fillna(1.0)
    month_idx = 0.5 + 0.5 * month_idx  # damp the noise
    spec_share = appt.specialty.value_counts(normalize=True)
    spec_w = spec_share / spec_share.mean()

    res = pd.read_csv(RAW / "sunrise_resource_utilisation.csv")
    res["occ"] = res.occupied_beds / res.total_beds
    load = res.groupby("hospital").occ.mean()
    load = (load / load.mean()).clip(0.7, 1.3)
    return month_idx, spec_w, load


def build(seed=42):
    rng = np.random.default_rng(seed)
    month_idx, spec_w, load = anchors()
    weeks = pd.date_range(end=AS_OF - pd.Timedelta(weeks=1), periods=N_WEEKS, freq="W-MON")
    rows = []
    for region, rload in load.items():
        for sku, (name, spec, cost, peak) in SKUS.items():
            base = 400 * spec_w.get(spec, 1.0) * rload * rng.uniform(0.7, 1.3)
            for i, w in enumerate(weeks):
                season = month_idx[w.month]
                if peak:
                    season *= 1 + 0.25 * np.cos(2 * np.pi * (w.month - peak) / 12)
                trend = 1 + 0.10 * i / N_WEEKS
                noise = rng.normal(1.0, 0.06)
                rows.append((region, sku, w, max(1, round(base * season * trend * noise))))
    sales = pd.DataFrame(rows, columns=["region", "sku", "ds", "y"])

    # Current batches on hand (as of AS_OF), a few deliberately overstocked
    wk = sales.groupby(["region", "sku"]).y.apply(lambda s: s.tail(8).mean())
    brows, bid = [], 1
    for (region, sku), rate in wk.items():
        for _ in range(rng.integers(2, 5)):
            cover_weeks = rng.choice([4, 8, 14, 26, 60], p=[.25, .3, .2, .15, .10])
            stock = int(rate * cover_weeks * rng.uniform(0.3, 1.0))
            exp = AS_OF + pd.Timedelta(days=int(rng.integers(20, 540)))
            brows.append((f"B{bid:04d}", region, sku, SKUS[sku][0], stock, exp, SKUS[sku][2]))
            bid += 1
    batches = pd.DataFrame(brows, columns=["batch_id", "region", "sku", "sku_name",
                                           "stock_units", "expiry_date", "unit_cost"])
    return sales, batches


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    sales, batches = build(a.seed)
    sales.to_csv(OUT / "sales.csv", index=False)
    batches.to_csv(OUT / "batches.csv", index=False)
    print(f"sales: {len(sales)} rows, {sales.groupby(['region','sku']).ngroups} series | batches: {len(batches)}")
