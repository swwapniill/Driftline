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

sorted_anomalies = sorted(anomalies, key=lambda x: x['date'])

table_rows = ""
for a in sorted_anomalies:
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

featured = [sorted_anomalies[0]]
catchall_example = next((a for a in sorted_anomalies if a.get('top_driver', {}).get('is_catchall_bucket') or (a.get('secondary_driver') or {}).get('is_catchall_bucket')), None)
if catchall_example and catchall_example['date'] != featured[0]['date']:
    featured.append(catchall_example)

featured_html = ""
for a in featured:
    d = pd.to_datetime(a['date'], format='%Y%m%d').strftime('%b %d, %Y')
    featured_html += f"""
    <div class="featured-item">
      <div class="featured-date">{d}</div>
      <div class="featured-text">{a.get('explanation', '')}</div>
    </div>"""

# Synthetic no-clear-driver example, clearly labeled as such
synthetic_html = """
    <div class="featured-item">
      <div class="featured-date">Synthetic test case — no real anomaly in this dataset triggered this scenario</div>
      <div class="featured-text">The increase appears to be spread across multiple factors, so there is no single clear cause. Traffic from Google rose by 8.2 points, accounting for 28% of the change, while mobile device usage grew by 7.5 points, contributing 25.5% of the shift.</div>
    </div>"""

generated_at = datetime.now(timezone.utc).strftime('%b %d, %Y, %H:%M UTC')

diagram_svg = """
<svg viewBox="0 0 760 100" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto;">
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#4C5561"/>
    </marker>
  </defs>
  <style>
    .box { fill: #10151C; stroke: #2A3138; stroke-width: 1; }
    .label { fill: #E6EDF3; font-family: 'IBM Plex Mono', monospace; font-size: 12px; }
    .sub { fill: #8B949E; font-family: 'IBM Plex Sans', sans-serif; font-size: 10px; }
    .arrow { stroke: #4C5561; stroke-width: 1.5; marker-end: url(#arrow); }
  </style>
  <rect class="box" x="0" y="30" width="120" height="45" rx="3"/>
  <text class="label" x="60" y="50" text-anchor="middle">BigQuery</text>
  <text class="sub" x="60" y="65" text-anchor="middle">GA4 data</text>
  <line class="arrow" x1="120" y1="52" x2="150" y2="52"/>
  <rect class="box" x="152" y="30" width="120" height="45" rx="3"/>
  <text class="label" x="212" y="50" text-anchor="middle">Detection</text>
  <text class="sub" x="212" y="65" text-anchor="middle">z-score</text>
  <line class="arrow" x1="272" y1="52" x2="302" y2="52"/>
  <rect class="box" x="304" y="30" width="120" height="45" rx="3"/>
  <text class="label" x="364" y="50" text-anchor="middle">Diagnosis</text>
  <text class="sub" x="364" y="65" text-anchor="middle">driver breakdown</text>
  <line class="arrow" x1="424" y1="52" x2="454" y2="52"/>
  <rect class="box" x="456" y="30" width="120" height="45" rx="3" style="stroke:#F0883E"/>
  <text class="label" x="516" y="50" text-anchor="middle">Groq LLM</text>
  <text class="sub" x="516" y="65" text-anchor="middle">grounded explanation</text>
  <line class="arrow" x1="576" y1="52" x2="606" y2="52"/>
  <rect class="box" x="608" y="30" width="120" height="45" rx="3" style="stroke:#58A6FF"/>
  <text class="label" x="668" y="50" text-anchor="middle">Slack alert</text>
  <text class="sub" x="668" y="65" text-anchor="middle">real-time notify</text>
</svg>
"""

html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Driftline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0F1419; --panel: #161B22; --text: #E6EDF3; --muted: #8B949E; --border: #2A3138;
  }}
  * {{ box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'IBM Plex Sans', sans-serif; margin: 0; padding: 48px 24px; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; font-weight: 600; margin: 0 0 4px 0; }}
  .pitch {{ color: var(--text); font-size: 1.05rem; margin-bottom: 8px; line-height: 1.5; max-width: 640px; }}
  .updated {{ color: var(--muted); font-size: 0.78rem; font-family: 'IBM Plex Mono', monospace; margin-bottom: 40px; }}
  .section-label {{ color: var(--muted); font-size: 0.78rem; letter-spacing: 0.02em; margin-bottom: 12px; font-family: 'IBM Plex Mono', monospace; }}
  .kpi-row {{ display: flex; gap: 1px; background: var(--border); border: 1px solid var(--border); margin-bottom: 40px; }}
  .kpi {{ flex: 1; background: var(--panel); padding: 20px 24px; }}
  .kpi-value {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem; font-weight: 500; }}
  .kpi-label {{ color: var(--muted); font-size: 0.82rem; margin-top: 4px; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); padding: 24px; margin-bottom: 16px; }}
  .panel-title {{ font-size: 0.95rem; font-weight: 500; margin-bottom: 16px; color: var(--text); }}
  .panel-note {{ color: var(--muted); font-size: 0.82rem; margin-top: 14px; line-height: 1.5; }}
  .section {{ margin-bottom: 48px; }}
  .featured-item {{ padding: 16px 0; border-bottom: 1px solid var(--border); }}
  .featured-item:last-child {{ border-bottom: none; }}
  .featured-date {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: var(--muted); margin-bottom: 6px; }}
  .featured-text {{ font-size: 0.92rem; line-height: 1.6; color: var(--text); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  th {{ text-align: left; color: var(--muted); font-weight: 500; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 0.82rem; }}
  td {{ padding: 12px; border-bottom: 1px solid var(--border); font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; }}
  .row-summary {{ cursor: pointer; }}
  .row-summary:hover {{ background: #1C232C; }}
  .row-detail {{ display: none; }}
  .row-detail.open {{ display: table-row; }}
  .explanation-cell {{ font-family: 'IBM Plex Sans', sans-serif; color: var(--muted); font-size: 0.85rem; line-height: 1.5; background: #10151C; }}
  .badge {{ border: 1px solid; padding: 2px 8px; font-size: 0.78rem; border-radius: 3px; }}
  .badge-link {{ display: inline-block; margin-top: 12px; }}
  .badge-link img {{ display: block; }}
  .readme-link {{ color: var(--muted); font-size: 0.85rem; }}
  .readme-link a {{ color: #58A6FF; }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 24px; }}
</style>
</head>
<body>
<div class="container">

  <h1>Driftline</h1>
  <div class="pitch">Detects e-commerce anomalies, explains them from real numbers only, runs itself daily.</div>
  <div class="updated">Last updated: {generated_at}</div>

  <div class="section">
    <div class="section-label">What it catches</div>
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-value">{days_monitored}</div><div class="kpi-label">Days monitored</div></div>
      <div class="kpi"><div class="kpi-value">{total_anomalies}</div><div class="kpi-label">Anomalies detected</div></div>
      <div class="kpi"><div class="kpi-value" style="color:#F0883E">{spikes}</div><div class="kpi-label">Spikes</div></div>
      <div class="kpi"><div class="kpi-value" style="color:#58A6FF">{dips}</div><div class="kpi-label">Dips</div></div>
    </div>
    <div class="panel">
      <div class="panel-title">Daily purchases, GA4 e-commerce sample, {date_range_start} to {date_range_end}</div>
      {chart_html}
    </div>
  </div>

  <div class="section">
    <div class="section-label">How it explains, without guessing</div>
    <div class="panel">
      <div class="panel-title">Real examples — explanations generated only from the numbers shown</div>
      {featured_html}
      {synthetic_html}
      <div class="panel-note">Every anomaly below (click to expand) gets the same treatment: only cites numbers it was given, and says so plainly when a driver is unclear or there isn't enough history yet.</div>
    </div>
    <div class="panel">
      <div class="panel-title">Full anomaly log</div>
      <table>
        <thead><tr><th>Date</th><th>Type</th><th>Top driver</th><th>Contribution</th></tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-label">How it runs</div>
    <div class="panel">
      <div class="panel-title">BigQuery → detection → diagnosis → Groq → Slack, daily, unattended</div>
      {diagram_svg}
      <a class="badge-link" href="https://github.com/swwapniill/driftline/actions" target="_blank">
        <img src="https://github.com/swwapniill/driftline/actions/workflows/daily-pipeline.yml/badge.svg" alt="Pipeline status">
      </a>
      <div class="panel-note">This page and each Slack alert are generated by the same scheduled run — click the badge for real run history and logs.</div>
    </div>
    <div class="readme-link">For full testing methodology and known limitations, see the <a href="https://github.com/swwapniill/driftline" target="_blank">README</a>.</div>
  </div>

  <footer>Detection: 14-day rolling z-score (threshold 1.8). Explanations generated via a grounded LLM layer (Groq, openai/gpt-oss-120b).</footer>
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

print("Dashboard written to docs/index.html")
