-- Regional drill-down (used by dashboard + weekly report)
-- Next-13-week forecast vs previous 13 weeks of actuals, by region
SELECT f.region,
       ROUND(SUM(f.yhat)) AS forecast_units,
       (SELECT SUM(s.y) FROM sales s WHERE s.region = f.region
          AND s.ds >= (SELECT DATE(MAX(ds), '-84 day') FROM sales)) AS last_13w_actual
FROM forecast f GROUP BY f.region;

-- Expiry exposure by region and tier
SELECT region, risk_tier, COUNT(*) AS batches, SUM(at_risk_units) AS units, ROUND(SUM(value_at_risk),2) AS value_at_risk
FROM expiry_alerts GROUP BY region, risk_tier;
