from google.cloud import bigquery

client = bigquery.Client(project="anomaly-explainer")

dataset = bigquery.Dataset("anomaly-explainer.analytics")
dataset.location = "US"

client.create_dataset(dataset)
print("Dataset created.")
