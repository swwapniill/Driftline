from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project="anomaly-explainer")

query = """
SELECT day, traffic_source, SUM(purchase_events) as purchases
FROM `anomaly-explainer.analytics.daily_purchases`
WHERE day BETWEEN '20201109' AND '20201123'
GROUP BY day, traffic_source
ORDER BY day, traffic_source
"""

df = client.query(query).result().to_dataframe()

# baseline = average per traffic source over the 14 days BEFORE Nov 23
baseline = df[df['day'] < '20201123'].groupby('traffic_source')['purchases'].mean()

# actual = Nov 23 value per traffic source
actual = df[df['day'] == '20201123'].groupby('traffic_source')['purchases'].sum()

comparison = pd.DataFrame({'baseline_avg': baseline, 'actual_nov23': actual}).fillna(0)
comparison['change'] = comparison['actual_nov23'] - comparison['baseline_avg']
comparison = comparison.sort_values('change', ascending=False)

print(comparison)
