# Weekly Pharma Demand & Expiry Report - week of 2026-11-02

## Forecast accuracy (13-week holdout backtest)
- Mean MAPE: **6.5%** (target < 15%) - MET
- Series under 15%: 100% of 32

## Regional demand outlook (next 13 weeks vs previous 13)
| region              |   forecast_13w |   actual_prev_13w |   change_pct |
|:--------------------|---------------:|------------------:|-------------:|
| Sunrise East        |          40455 |             39684 |          1.9 |
| Sunrise Main Campus |          51629 |             50186 |          2.9 |
| Sunrise North       |          47992 |             47061 |          2   |
| Sunrise South       |          41662 |             41113 |          1.3 |

## Expiry risk summary
| risk_tier   |   batches |   units |   value_at_risk |
|:------------|----------:|--------:|----------------:|
| High        |         8 |   26214 |        188275   |
| Low         |         3 |    6862 |          8482.2 |
| Medium      |         6 |   37752 |        757522   |

## Top 10 batches to act on (redistribute / discount / return)
| region              | sku_name          | batch_id   | expiry_date   |   days_to_expiry |   stock_units |   at_risk_units |   value_at_risk | risk_tier   |
|:--------------------|:------------------|:-----------|:--------------|-----------------:|--------------:|----------------:|----------------:|:------------|
| Sunrise Main Campus | Timolol eye drops | B0048      | 2027-02-25    |              115 |         22036 |           14796 |        665820   | Medium      |
| Sunrise East        | Timolol eye drops | B0022      | 2027-01-28    |               87 |          8460 |            3332 |        149940   | High        |
| Sunrise North       | Timolol eye drops | B0076      | 2027-03-14    |              132 |         10666 |            1289 |         58005   | Medium      |
| Sunrise North       | Omeprazole 20mg   | B0069      | 2027-03-29    |              147 |         21181 |           10898 |         19616.4 | Medium      |
| Sunrise North       | Amoxicillin 500mg | B0054      | 2026-12-30    |               58 |          8444 |            4229 |         12687   | High        |
| Sunrise East        | Atorvastatin 10mg | B0008      | 2027-01-02    |               61 |          8981 |            4788 |         10533.6 | High        |
| Sunrise East        | Ibuprofen 400mg   | B0016      | 2027-04-18    |              167 |         14777 |            6409 |          7690.8 | Medium      |
| Sunrise Main Campus | Amlodipine 5mg    | B0025      | 2026-11-22    |               20 |          5557 |            4110 |          6165   | High        |
| Sunrise East        | Paracetamol 500mg | B0021      | 2026-11-23    |               21 |          8404 |            7120 |          5696   | High        |
| Sunrise North       | Omeprazole 20mg   | B0070      | 2027-04-15    |              164 |          3398 |            1929 |          3472.2 | Medium      |
