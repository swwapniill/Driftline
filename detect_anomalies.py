from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project="anomaly-explainer")

query = """
SELECT day, SUM(purchase_events) as total_purchases
FROM `anomaly-explainer.analytics.daily_purchases`
GROUP BY day
ORDER BY day
"""

df = client.query(query).result().to_dataframe()
df['day'] = pd.to_datetime(df['day'], format='%Y%m%d')
df = df.sort_values('day').reset_index(drop=True)

window = 14

df['rolling_mean'] = df['total_purchases'].rolling(window=window, min_periods=window).mean()
df['rolling_std'] = df['total_purchases'].rolling(window=window, min_periods=window).std()

df['z_score'] = (df['total_purchases'] - df['rolling_mean']) / df['rolling_std']

threshold = 1.8
df['is_anomaly'] = df['z_score'].abs() > threshold

anomalies = df[df['is_anomaly']]

print(anomalies[['day', 'total_purchases', 'rolling_mean', 'z_score']])
print("Total anomalies found:", len(anomalies))
