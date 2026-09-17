from google.cloud import bigquery

client = bigquery.Client(project="anomaly-explainer")

query = """
SELECT COUNT(*) as total_rows, COUNT(DISTINCT day) as unique_days
FROM `anomaly-explainer.analytics.daily_purchases`
"""

for row in client.query(query).result():
    print("Total rows:", row.total_rows)
    print("Unique days:", row.unique_days)
