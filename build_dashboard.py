from google.cloud import bigquery
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime, timezone

client = bigquery.Client(project="anomaly-explainer")

query = """
SELECT day, SUM(purchase_events) as total_purchases
FROM `anomaly-explainer.analytics.daily_purchases`
GROUP BY day
ORDER BY day
"""
df = client.query(query).result().to_dataframe()
df['day'] = pd.to_datetime(df['day'], format='%Y%m%d')
df = df.sort_values('day').reset_index(drop=True)

with open('anomaly_breakdown.json') as f:
    anomalies = json.load(f)

anomaly_dates = {a['date']: a for a in anomalies}

total_anomalies = len(anomalies)
date_range_start = df['day'].min().strftime('%b %d, %Y')
date_range_end = df['day'].max().strftime('%b %d, %Y')
days_monitored = len(df)
spikes = sum(1 for a in anomalies if a.get('top_driver') and a['top_driver']['delta'] > 0)
dips = total_anomalies - spikes

chart_dates, chart_values, point_colors, point_sizes = [], [], [], []
for _, row in df.iterrows():
    date_str = row['day'].strftime('%Y%m%d')
    chart_dates.append(row['day'].strftime('%Y-%m-%d'))
    chart_values.append(int(row['total_purchases']))
    if date_str in anomaly_dates:
        top = anomaly_dates[date_str].get('top_driver')
        is_spike = top and top['delta'] > 0
        point_colors.append('#F0883E' if is_spike else '#58A6FF')
        point_sizes.append(11)
    else:
        point_colors.append('#4C5561')
        point_sizes.append(5)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=chart_dates, y=chart_values,
    mode='lines+markers',
    line=dict(color='#39424D', width=1.5),
    marker=dict(color=point_colors, size=point_sizes, line=dict(width=0)),
    hovertemplate='%{x}<br>Purchases: %{y}<extra></extra>'
))
fig.update_layout(
    plot_bgcolor='#161B22',
    paper_bgcolor='#161B22',
    font=dict(family='IBM Plex Mono, monospace', color='#8B949E', size=12),
    xaxis=dict(gridcolor='#2A3138', showline=False),
    yaxis=dict(gridcolor='#2A3138', showline=False, title='Daily purchases'),
    margin=dict(l=50, r=30, t=20, b=40),
    height=380,
    hovermode='closest'
)
chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

# Build expandable table rows using <details>/<summary> — no JS needed
table_rows = ""
for a in sorted(anomalies, key=lambda x: x['date']):
    d = pd.to_datetime(a['date'], format='%Y%m%d').strftime('%b %d, %Y')
    top = a.get('top_driver')
    direction = "Spike" if top and top['delta'] > 0 else "Dip"
    badge_color = "#F0883E" if direction == "Spike" else "#58A6FF"
    top_text = f"{top['dimension'].replace('_', ' ')}: {top['value']}" if top else "—"
    if top and top.get('is_catchall_bucket'):
        top_text += " (unclear category)"
    contribution = f"{top['contribution_pct']}%" if top else "—"
    explanation = a.get('explanation', 'No explanation generated.')

    table_rows += f"""
    <tr class="row-summary">
      <td>{d}</td>
      <td><span class="badge" style="color:{badge_color}; border-color:{badge_color}">{direction}</span></td>
      <td>{top_text}</td>
      <td>{contribution}</td>
    </tr>
    <tr class="row-detail">
      <td colspan="4" class="explanation-cell">{explanation}</td>
    </tr>"""

generated_at = datetime.now(timezone.utc).strftime('%b %d, %Y, %H:%M UTC')

html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Driftline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0F1419;
    --panel: #161B22;
    --text: #E6EDF3;
    --muted: #8B949E;
    --border: #2A3138;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Sans', sans-serif;
    margin: 0;
    padding: 48px 24px;
  }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; font-weight: 600; margin: 0 0 4px 0; }}
  .subtitle {{ color: var(--muted); font-size: 0.95rem; margin-bottom: 8px; }}
  .updated {{ color: var(--muted); font-size: 0.78rem; font-family: 'IBM Plex Mono', monospace; margin-bottom: 40px; }}
  .kpi-row {{
    display: flex; gap: 1px; background: var(--border);
    border: 1px solid var(--border); margin-bottom: 40px;
  }}
  .kpi {{ flex: 1; background: var(--panel); padding: 20px 24px; }}
  .kpi-value {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem; font-weight: 500; }}
  .kpi-label {{ color: var(--muted); font-size: 0.82rem; margin-top: 4px; }}
  .panel {{
    background: var(--panel); border: 1px solid var(--border);
    padding: 24px; margin-bottom: 32px;
  }}
  .panel-title {{ font-size: 0.95rem; font-weight: 500; margin-bottom: 16px; color: var(--text); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  th {{
    text-align: left; color: var(--muted); font-weight: 500;
    padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 0.82rem;
  }}
  td {{
    padding: 12px; border-bottom: 1px solid var(--border);
    font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem;
  }}
  .row-summary {{ cursor: pointer; }}
  .row-summary:hover {{ background: #1C232C; }}
  .row-detail {{ display: none; }}
  .row-detail.open {{ display: table-row; }}
  .explanation-cell {{
    font-family: 'IBM Plex Sans', sans-serif; color: var(--muted);
    font-size: 0.85rem; line-height: 1.5; background: #10151C;
  }}
  .badge {{
    border: 1px solid; padding: 2px 8px; font-size: 0.78rem; border-radius: 3px;
  }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 24px; }}
</style>
</head>
<body>
<div class="container">
  <h1>Driftline</h1>
  <div class="subtitle">Driftline — anomaly detection & root-cause explanation for e-commerce metrics. GA4 sample dataset, {date_range_start} to {date_range_end}</div>
  <div class="updated">Last updated: {generated_at}</div>

  <div class="kpi-row">
    <div class="kpi"><div class="kpi-value">{days_monitored}</div><div class="kpi-label">Days monitored</div></div>
    <div class="kpi"><div class="kpi-value">{total_anomalies}</div><div class="kpi-label">Anomalies detected</div></div>
    <div class="kpi"><div class="kpi-value" style="color:#F0883E">{spikes}</div><div class="kpi-label">Spikes</div></div>
    <div class="kpi"><div class="kpi-value" style="color:#58A6FF">{dips}</div><div class="kpi-label">Dips</div></div>
  </div>

  <div class="panel">
    <div class="panel-title">Daily purchases, with detected anomalies</div>
    {chart_html}
  </div>

  <div class="panel">
    <div class="panel-title">Anomaly log — click a row for the full explanation</div>
    <table>
      <thead><tr><th>Date</th><th>Type</th><th>Top driver</th><th>Contribution</th></tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>

  <footer>Detection: 14-day rolling z-score (threshold 1.8). Explanations generated via a grounded LLM layer (Groq, openai/gpt-oss-120b) — see repo README for methodology and known limitations. Pipeline runs daily via GitHub Actions.</footer>
</div>

<script>
document.querySelectorAll('.row-summary').forEach(row => {{
  row.addEventListener('click', () => {{
    const detail = row.nextElementSibling;
    detail.classList.toggle('open');
  }});
}});
</script>
</body>
</html>
"""

import os
os.makedirs('docs', exist_ok=True)
with open('docs/index.html', 'w') as f:
    f.write(html_output)

print("Dashboard written to dashboard/index.html")
