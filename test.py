from google.cloud import bigquery

client = bigquery.Client(project="anomaly-explainer")

query = """
SELECT
  _TABLE_SUFFIX as day,
  traffic_source.source as traffic_source,
  device.category as device_type,
  geo.country as country,
  COUNT(*) as purchase_events
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE event_name = 'purchase'
GROUP BY day, traffic_source, device_type, country
ORDER BY day
LIMIT 20
"""

result = client.query(query).result()

for row in result:
    print(row.day, row.traffic_source, row.device_type, row.country, row.purchase_events)
