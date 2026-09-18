from google.cloud import bigquery
import pandas as pd
import json
import argparse
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from date_mapper import get_simulated_date
from prompt_template import SYSTEM_PROMPT

load_dotenv()
client = bigquery.Client(project="anomaly-explainer")
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

def check_anomaly(target_date):
    query = """
    SELECT day, SUM(purchase_events) as total_purchases
    FROM `anomaly-explainer.analytics.daily_purchases`
    GROUP BY day
    ORDER BY day
    """
    df = client.query(query).result().to_dataframe()
    df['day'] = pd.to_datetime(df['day'], format='%Y%m%d')
    df = df.sort_values('day').reset_index(drop=True)

    target_dt = pd.to_datetime(target_date, format='%Y%m%d')
    target_idx = df[df['day'] == target_dt].index

    if len(target_idx) == 0:
        return None

    idx = target_idx[0]
    if idx < 14:
        return {"date": target_date, "status": "insufficient_baseline"}

    window = df.iloc[idx-14:idx]['total_purchases']
    actual = df.iloc[idx]['total_purchases']
    rolling_mean = window.mean()
    rolling_std = window.std()
    z_score = (actual - rolling_mean) / rolling_std

    is_anomaly = abs(z_score) > 1.8
    return {
        "date": target_date,
        "status": "anomaly" if is_anomaly else "normal",
        "actual": int(actual),
        "rolling_mean": round(float(rolling_mean), 1),
        "z_score": round(float(z_score), 2)
    }

def diagnose_dimension(anomaly_date, dimension):
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
    return {
        "dimension": dimension,
        "value": top.name,
        "delta": round(float(top['delta']), 1),
        "contribution_pct": round(float(top['contribution_pct']), 1),
        "is_catchall_bucket": bool(is_catchall)
    }

def diagnose_anomaly(anomaly_date):
    drivers = []
    for dim in ['traffic_source', 'device_type', 'country']:
        d = diagnose_dimension(anomaly_date, dim)
        if d:
            drivers.append(d)
    drivers = sorted(drivers, key=lambda x: abs(x['delta']), reverse=True)

    if len(drivers) >= 2 and drivers[0]['contribution_pct'] < 40:
        driver_status = "distributed, no dominant driver"
    else:
        driver_status = "concentrated"

    return {
        "driver_status": driver_status,
        "top_driver": drivers[0] if len(drivers) > 0 else None,
        "secondary_driver": drivers[1] if len(drivers) > 1 else None
    }

def explain_anomaly(anomaly_data):
    user_prompt = f"Explain this anomaly using only the data below:\n\n{json.dumps(anomaly_data, indent=2)}"
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content

def send_to_slack(result, explanation):
    formatted_date = datetime.strptime(result['date'], '%Y%m%d').strftime('%B %d, %Y')
    message = (
        f"*Anomaly Detected — {formatted_date}*\n"
        f"Actual: {result['actual']} | Rolling avg: {result['rolling_mean']} | Z-score: {result['z_score']}\n\n"
        f"{explanation}"
    )
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    return response.status_code

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Override date (YYYYMMDD) for testing", default=None)
    args = parser.parse_args()

    target_date = args.date if args.date else get_simulated_date()
    print(f"Checking date: {target_date}")
    result = check_anomaly(target_date)
    print(json.dumps(result, indent=2))

    if result and result['status'] == 'anomaly':
        print("\nAnomaly detected — running diagnosis...")
        diagnosis = diagnose_anomaly(target_date)
        result.update(diagnosis)
        print(json.dumps(diagnosis, indent=2))

        print("\nGenerating explanation...")
        explanation = explain_anomaly(result)
        print("\n--- EXPLANATION ---")
        print(explanation)

        print("\nSending to Slack...")
        status = send_to_slack(result, explanation)
        print("Slack status code:", status)
    else:
        print("No anomaly detected — nothing sent to Slack.")
