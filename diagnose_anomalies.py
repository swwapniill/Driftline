from google.cloud import bigquery
import pandas as pd
import json

client = bigquery.Client(project="anomaly-explainer")

anomaly_dates = ['20201117','20201120','20201123','20201124','20201220','20210112','20210114','20210120','20210122']

def diagnose(anomaly_date, dimension):
    query = f"""
    SELECT day, {dimension} as dim_value, SUM(purchase_events) as purchases
    FROM `anomaly-explainer.analytics.daily_purchases`
    WHERE day BETWEEN
      FORMAT_DATE('%Y%m%d', DATE_SUB(PARSE_DATE('%Y%m%d', '{anomaly_date}'), INTERVAL 14 DAY))
      AND '{anomaly_date}'
    GROUP BY day, dim_value
    """
    df = client.query(query).result().to_dataframe()

    baseline_df = df[df['day'] < anomaly_date]
    actual_df = df[df['day'] == anomaly_date]

    baseline_avg = baseline_df.groupby('dim_value')['purchases'].mean()
    actual = actual_df.groupby('dim_value')['purchases'].sum()

    comp = pd.DataFrame({'baseline_avg': baseline_avg, 'actual': actual}).fillna(0)
    comp['delta'] = comp['actual'] - comp['baseline_avg']

    total_delta = comp['delta'].sum()
    comp['contribution_pct'] = (comp['delta'] / total_delta * 100) if total_delta != 0 else 0
    comp = comp.reindex(comp['delta'].abs().sort_values(ascending=False).index)

    if len(comp) == 0:
        return None
    top = comp.iloc[0]
    is_catchall = top.name in ['other_country', '<Other>', 'other_source']
    return {"dimension": dimension, "value": top.name, "delta": round(top['delta'], 1), "contribution_pct": round(top['contribution_pct'], 1), "is_catchall_bucket": is_catchall}

def diagnose_date(date, anomaly_dates_set):
    drivers = []
    for dim in ['traffic_source', 'device_type', 'country']:
        d = diagnose(date, dim)
        if d:
            drivers.append(d)
    drivers = sorted(drivers, key=lambda x: abs(x['delta']), reverse=True)

    if len(drivers) >= 2 and drivers[0]['contribution_pct'] < 40:
        driver_status = "distributed, no dominant driver"
    else:
        driver_status = "concentrated"

    entry = {
        "date": date,
        "driver_status": driver_status,
        "top_driver": drivers[0] if len(drivers) > 0 else None,
        "secondary_driver": drivers[1] if len(drivers) > 1 else None
    }
    return entry

results = []
for date in anomaly_dates:
    entry = diagnose_date(date, anomaly_dates)
    results.append(entry)
    print(json.dumps(entry, indent=2))

with open('anomaly_breakdown.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved to anomaly_breakdown.json")

# Manual test: pick an ordinary (non-anomaly) day and confirm 'distributed' logic works
print("\n--- Sanity check on a normal day (2020-12-05) ---")
normal_day_result = diagnose_date('20201205', anomaly_dates)
print(json.dumps(normal_day_result, indent=2))
