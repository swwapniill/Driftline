from google.cloud import bigquery

client = bigquery.Client(project="anomaly-explainer")

query = """
SELECT geo.country as country, COUNT(*) as cnt
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE event_name = 'purchase'
GROUP BY country
ORDER BY cnt DESC
LIMIT 10
"""

for row in client.query(query).result():
    print(row.country, row.cnt)
