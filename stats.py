import mlflow, pandas as pd

mlflow.set_tracking_uri('sqlite:///mlflow.db')
r = mlflow.search_runs(experiment_names=['pharma_demand_forecast'])
print('total runs:', len(r))

cols = ['tags.mlflow.runName', 'metrics.mape_mean', 'metrics.pct_series_under_15']
print(r[cols].sort_values('metrics.mape_mean').to_string())

a = pd.read_csv('outputs/accuracy.csv')
print('best config MAPE: mean %.2f, median %.2f, max %.2f' % (a.mape.mean(), a.mape.median(), a.mape.max()))
print(a.groupby('region').mape.mean().round(2))

e = pd.read_csv('outputs/expiry_alerts.csv')
print(e.groupby('risk_tier').agg(batches=('batch_id', 'count'),
                                 units=('at_risk_units', 'sum'),
                                 value=('value_at_risk', 'sum')).round(0))