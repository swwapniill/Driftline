from google.cloud import bigquery

client = bigquery.Client(project="anomaly-explainer")

query = """
CREATE OR REPLACE TABLE `anomaly-explainer.analytics.daily_purchases` AS
SELECT
  _TABLE_SUFFIX as day,
  CASE
    WHEN traffic_source.source IN ('google', '<Other>', '(direct)', '(data deleted)', 'shop.googlemerchandisestore.com')
    THEN traffic_source.source
    ELSE 'other_source'
  END as traffic_source,
  device.category as device_type,
  CASE
    WHEN geo.country IN ('United States', 'India', 'Canada', 'United Kingdom', 'Spain', 'France', 'China', 'Germany', 'Taiwan', 'Japan')
    THEN geo.country
    ELSE 'other_country'
  END as country,
  COUNT(*) as purchase_events
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE event_name = 'purchase'
GROUP BY day, traffic_source, device_type, country
"""

client.query(query).result()
print("Table created successfully.")
