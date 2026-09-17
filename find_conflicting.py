import json

with open('anomaly_breakdown.json') as f:
    anomalies = json.load(f)

for a in anomalies:
    top = a.get('top_driver')
    sec = a.get('secondary_driver')
    if top and sec:
        if (top['delta'] > 0 and sec['delta'] < 0) or (top['delta'] < 0 and sec['delta'] > 0):
            print(json.dumps(a, indent=2))
