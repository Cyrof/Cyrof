#!/usr/bin/env python3
"""Create a clean, static GitHub contribution graph SVG (last 365 days)."""
import json
import os
from datetime import date, timedelta
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USERNAME = os.getenv("GITHUB_STATS_USERNAME", "Cyrof")
TOKEN = os.environ.get("GH_GRAPH_TOKEN")
OUTPUT = Path("dist/stats/activity-graph.svg")


def fetch_contributions(username: str, token: str) -> dict[date, int]:
    query = """query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    req = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": username}}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "weekly-github-activity-graph"},
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        raise RuntimeError(f"GitHub GraphQL failed: {payload.get('errors', payload)}")
    days = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {date.fromisoformat(day["date"]): day["contributionCount"]
            for week in days for day in week["contributionDays"]}


def render_svg(username: str, counts: dict[date, int], today: date) -> str:
    first = today - timedelta(days=364)
    grid_start = first - timedelta(days=(first.weekday() + 1) % 7)
    weeks = (today - grid_start).days // 7 + 1
    cell, gap, pitch = 10, 3, 13
    grid_left, grid_top = 49, 104
    width, height = grid_left + weeks * pitch + 22, 246
    palette = ("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353")

    def level(value: int) -> int:
        return 0 if value == 0 else 1 if value < 3 else 2 if value < 6 else 3 if value < 10 else 4

    total = sum(counts.get(first + timedelta(days=i), 0) for i in range(365))
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(username)} GitHub contributions over the past 365 days">',
        '<rect width="100%" height="100%" rx="12" fill="#0d1117"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        f'<text x="24" y="34" font-size="19" font-weight="700" fill="#f0f6fc">{escape(username)} — Contribution Activity</text>',
        f'<text x="24" y="57" font-size="12" fill="#8b949e">{total:,} contributions in the last 365 days</text>',
        '<line x1="24" y1="72" x2="' + str(width-24) + '" y2="72" stroke="#30363d"/>',
    ]

    # Month names are in a distinct row above the grid, below the separator.
    last_month = None
    for col in range(weeks):
        sunday = grid_start + timedelta(days=7 * col)
        representative = sunday + timedelta(days=3)
        if first <= representative <= today and representative.month != last_month:
            x = grid_left + col * pitch
            if x < width - 45:
                lines.append(f'<text x="{x}" y="91" font-size="11" fill="#8b949e">{representative:%b}</text>')
            last_month = representative.month

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        y = grid_top + row * pitch + 9
        lines.append(f'<text x="19" y="{y}" font-size="11" fill="#8b949e">{label}</text>')

    for col in range(weeks):
        for row in range(7):
            day = grid_start + timedelta(days=col * 7 + row)
            if not first <= day <= today:
                continue
            count = counts.get(day, 0)
            x, y = grid_left + col * pitch, grid_top + row * pitch
            lines.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{palette[level(count)]}"><title>{day.isoformat()}: {count} contributions</title></rect>')

    legend_y = 218
    lines.append(f'<text x="{width-174}" y="{legend_y+9}" font-size="11" fill="#8b949e">Less</text>')
    for i, color in enumerate(palette):
        lines.append(f'<rect x="{width-135+i*14}" y="{legend_y}" width="10" height="10" rx="2" fill="{color}"/>')
    lines += [f'<text x="{width-58}" y="{legend_y+9}" font-size="11" fill="#8b949e">More</text>', '</g>', '</svg>']
    return '\n'.join(lines)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("GH_GRAPH_TOKEN is required to fetch contribution data")
    counts = fetch_contributions(USERNAME, TOKEN)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_svg(USERNAME, counts, date.today()), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(counts)} days fetched)")


if __name__ == "__main__":
    main()

