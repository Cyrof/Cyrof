#!/usr/bin/env python3
"""Render the past year's GitHub contribution calendar as a static SVG."""
import json
import os
from datetime import date, timedelta
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USERNAME = os.environ.get('GITHUB_STATS_USERNAME', 'Cyrof')
TOKEN = os.environ['GH_GRAPH_TOKEN']
OUTPUT = Path('dist/stats/activity-graph.svg')

query = '''query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}'''
req = Request('https://api.github.com/graphql',
    data=json.dumps({'query': query, 'variables': {'login': USERNAME}}).encode(),
    headers={'Authorization': f'Bearer {TOKEN}',
             'Content-Type': 'application/json', 'User-Agent': 'github-weekly-activity-graph'},
    method='POST')
with urlopen(req, timeout=30) as response:
    payload = json.load(response)
if payload.get('errors') or not payload.get('data', {}).get('user'):
    raise RuntimeError(f'GitHub GraphQL failed: {payload.get("errors", payload)}')
calendar = payload['data']['user']['contributionsCollection']['contributionCalendar']
counts = {date.fromisoformat(day['date']): day['contributionCount']
          for week in calendar['weeks'] for day in week['contributionDays']}

# Last 365 days, aligned to Sunday columns.
today = date.today()
first = today - timedelta(days=364)
grid_start = first - timedelta(days=(first.weekday() + 1) % 7)
weeks = ((today - grid_start).days // 7) + 1
cell, gap, left, top = 10, 3, 45, 57
pitch = cell + gap
width = left + weeks * pitch + 20
height = top + 7 * pitch + 48
colors = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']

def level(n):
    return 0 if n == 0 else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4

parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub contribution activity in the past year">',
         '<rect width="100%" height="100%" rx="10" fill="#0d1117"/>',
         '<g fill="#c9d1d9" font-family="Arial, sans-serif">',
         f'<text x="18" y="29" font-weight="bold" font-size="16">{escape(USERNAME)} — Contribution Activity</text>',
         f'<text x="18" y="45" font-size="10" fill="#8b949e">Past 365 days · {sum(counts.get(first + timedelta(days=i),0) for i in range(365))} contributions</text>']
for label, row in [('Mon', 1), ('Wed', 3), ('Fri', 5)]:
    parts.append(f'<text x="18" y="{top + row * pitch + 9}" font-size="10" fill="#8b949e">{label}</text>')
previous_month = None
for col in range(weeks):
    sunday = grid_start + timedelta(days=7 * col)
    for row in range(7):
        day = sunday + timedelta(days=row)
        if not first <= day <= today:
            continue
        n = counts.get(day, 0)
        x, y = left + col * pitch, top + row * pitch
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{colors[level(n)]}"><title>{day.isoformat()}: {n} contributions</title></rect>')
        if row == 0 and day.month != previous_month:
            parts.append(f'<text x="{x}" y="{top - 8}" font-size="10" fill="#8b949e">{day.strftime("%b")}</text>')
            previous_month = day.month
parts += [f'<text x="{width - 168}" y="{height - 19}" font-size="10" fill="#8b949e">Less</text>']
for i, color in enumerate(colors):
    parts.append(f'<rect x="{width - 137 + i * 14}" y="{height - 28}" width="10" height="10" rx="2" fill="{color}"/>')
parts += [f'<text x="{width - 57}" y="{height - 19}" font-size="10" fill="#8b949e">More</text>', '</g>', '</svg>']
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text('\n'.join(parts), encoding='utf-8')
print(f'Wrote {OUTPUT}: {len(counts)} contribution days, {weeks} weeks')
