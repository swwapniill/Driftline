import os
import requests
from dotenv import load_dotenv

load_dotenv()
webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

payload = {"text": "Test message from Ops Anomaly Explainer pipeline setup."}
response = requests.post(webhook_url, json=payload)

print("Status code:", response.status_code)
print("Response:", response.text)
