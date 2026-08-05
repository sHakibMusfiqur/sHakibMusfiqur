#!/usr/bin/env python3
"""
GitHub Activity Graph SVG Generator
====================================
Fetches real contribution data from the GitHub GraphQL API and generates
a premium dark-theme SVG analytics card with a smooth line chart.

No external dependencies — Python 3.8+ stdlib only.

Usage:
    GITHUB_TOKEN=ghp_xxx python3 generate_activity.py <username> <output_dir>

Output:
    <output_dir>/activity.svg
"""

import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BG = "#0D1117"
CARD = "#111827"
BORDER = "#1F2937"
GRID = "#374151"
ACCENT1 = "#22D3EE"
ACCENT2 = "#3B82F6"
ACCENT3 = "#8B5CF6"
ACCENT4 = "#EC4899"
TEXT_PRIMARY = "#F9FAFB"
TEXT_SECONDARY = "#D1D5DB"
TEXT_MUTED = "#6B7280"
TEXT_DIM = "#4B5563"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Consolas, monospace"

# ---------------------------------------------------------------------------
# GraphQL query — last 60 days of contributions (we display ~30)
# ---------------------------------------------------------------------------
GRAPHQL_QUERY = """
query($login: String!, $start: DateTime!, $end: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $start, to: $end) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def api_request(url, token, data=None):
    """Make an authenticated GitHub API request."""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method="POST" if data else "GET")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "activity-graph-action")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_contribution_data(username, token):
    """Fetch the last 60 days of daily contribution data via GraphQL."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=59)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "login": username,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    }

    resp = api_request("https://api.github.com/graphql", token, data=payload)

    if "errors" in resp:
        raise RuntimeError(f"GraphQL errors: {resp['errors']}")

    cal = resp["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total_year = cal["totalContributions"]

    # Flatten weeks into a list of (date, count)
    days = []
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            dt = datetime.strptime(day["date"], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            days.append((dt, day["contributionCount"]))

    days.sort(key=lambda x: x[0])
    return days, total_year


def compute_stats(days):
    """Compute real stats from contribution data."""
    if not days:
        return {
            "total": 0,
            "current_streak": 0,
            "longest_streak": 0,
            "active_days": 0,
            "max_daily": 0,
            "avg_daily": 0.0,
        }

    counts = [c for _, c in days]
    total = sum(counts)
    active = sum(1 for c in counts if c > 0)
    max_daily = max(counts) if counts else 0
    avg_daily = total / len(counts) if counts else 0.0

    # Current streak: consecutive days ending at the last day
    current_streak = 0
    for count in reversed(counts):
        if count > 0:
            current_streak += 1
        else:
            break

    # Longest streak in the entire period
    longest_streak = 0
    streak = 0
    for count in counts:
        if count > 0:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0

    return {
        "total": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "active_days": active,
        "max_daily": max_daily,
        "avg_daily": avg_daily,
    }


def fmt(n):
    """Format a number with commas."""
    return f"{int(n):,}"


def esc(s):
    """Escape XML special characters."""
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def smooth_path(points):
    """Generate a smooth cubic-bezier SVG path through points using Catmull-Rom."""
    if len(points) < 2:
        return ""

    n = len(points)

    # Build control points via Catmull-Rom → cubic bezier conversion
    d_parts = []
    d_parts.append(f"M{points[0][0]:.1f},{points[0][1]:.1f}")

    for i in range(n - 1):
        p0 = points[max(i - 1, 0)]
        p1 = points[i]
        p2 = points[min(i + 1, n - 1)]
        p3 = points[min(i + 2, n - 1)]

        # Catmull-Rom to cubic bezier control points
        tension = 6.0
        cp1x = p1[0] + (p2[0] - p0[0]) / tension
        cp1y = p1[1] + (p2[1] - p0[1]) / tension
        cp2x = p2[0] - (p3[0] - p1[0]) / tension
        cp2y = p2[1] - (p3[1] - p1[1]) / tension

        d_parts.append(
            f"C{cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        )

    return " ".join(d_parts)


def generate_svg(days, stats, username):
    """Generate the complete SVG string from real data."""
    # --- Chart layout ---
    CARD_W = 980
    CHART_LEFT = 80
    CHART_RIGHT = 940
    CHART_TOP = 80
    CHART_BOTTOM = 266
    CHART_W = CHART_RIGHT - CHART_LEFT
    CHART_H = CHART_BOTTOM - CHART_TOP

    # We display the last 30 days
    display_days = days[-30:] if len(days) >= 30 else days
    n = len(display_days)

    counts = [c for _, c in display_days]
    max_val = max(counts) if counts else 1
    if max_val == 0:
        max_val = 1

    # Y-axis: auto-scale to nice round numbers
    y_ticks = 5
    y_step = math.ceil(max_val / y_ticks)
    y_max = y_step * y_ticks
    if y_max == 0:
        y_max = y_ticks

    # Map data to pixel coordinates
    def to_xy(i, val):
        x = CHART_LEFT + (i / max(n - 1, 1)) * CHART_W
        y = CHART_BOTTOM - (val / y_max) * CHART_H
        return (x, y)

    points = [to_xy(i, c) for i, c in enumerate(counts)]

    # --- Build SVG ---
    lines = []

    # SVG opening
    total_h = 380
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {total_h}" '
        f'width="{CARD_W}" height="{total_h}" role="img" '
        f'aria-label="Activity Graph — GitHub contribution analytics for {esc(username)}">'
    )

    # Defs
    lines.append("<defs>")
    # Line gradient (teal → blue → violet → pink)
    lines.append(
        '<linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="#22D3EE"/>'
        '<stop offset="33%" stop-color="#3B82F6"/>'
        '<stop offset="66%" stop-color="#8B5CF6"/>'
        '<stop offset="100%" stop-color="#EC4899"/>'
        "</linearGradient>"
    )
    # Area fill gradient
    lines.append(
        '<linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#22D3EE" stop-opacity="0.18"/>'
        '<stop offset="40%" stop-color="#3B82F6" stop-opacity="0.10"/>'
        '<stop offset="70%" stop-color="#8B5CF6" stop-opacity="0.04"/>'
        '<stop offset="100%" stop-color="#EC4899" stop-opacity="0"/>'
        "</linearGradient>"
    )
    # Glow gradient
    lines.append(
        '<linearGradient id="glowGrad" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="#22D3EE" stop-opacity="0.35"/>'
        '<stop offset="33%" stop-color="#3B82F6" stop-opacity="0.30"/>'
        '<stop offset="66%" stop-color="#8B5CF6" stop-opacity="0.25"/>'
        '<stop offset="100%" stop-color="#EC4899" stop-opacity="0.20"/>'
        "</linearGradient>"
    )
    # Glow filter
    lines.append(
        '<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feGaussianBlur stdDeviation="3" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
    )
    # Drop shadow filter
    lines.append(
        '<filter id="softShadow" x="-10%" y="-10%" width="120%" height="130%">'
        f'<feDropShadow dx="0" dy="4" stdDeviation="12" flood-color="#000" flood-opacity="0.35"/>'
        "</filter>"
    )
    # Clip path for chart area
    lines.append(
        f'<clipPath id="chartClip">'
        f'<rect x="{CHART_LEFT}" y="{CHART_TOP}" width="{CHART_W}" height="{CHART_H}"/>'
        f"</clipPath>"
    )
    # Stat card icon gradients
    for i, color in enumerate(["#22D3EE", "#3B82F6", "#8B5CF6", "#EC4899"]):
        lines.append(
            f'<linearGradient id="ic{i+1}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.22"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0.08"/>'
            f"</linearGradient>"
        )
        lines.append(
            f'<linearGradient id="stat{i+1}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.15"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0.05"/>'
            f"</linearGradient>"
        )
    lines.append("</defs>")

    # Card background
    card_h = total_h - 2
    lines.append(
        f'<rect x="1" y="1" width="{CARD_W-2}" height="{card_h}" rx="20" '
        f'fill="{CARD}" stroke="{BORDER}" stroke-width="1" filter="url(#softShadow)"/>'
    )
    lines.append(
        f'<rect x="1" y="1" width="{CARD_W-2}" height="1" rx="0.5" '
        f'fill="url(#lineGrad)" opacity="0.5"/>'
    )

    # Header
    lines.append(
        f'<rect x="32" y="26" width="28" height="28" rx="8" '
        f'fill="#22D3EE" fill-opacity="0.15"/>'
    )
    lines.append(
        '<path d="M40 36l4 4 8-8" stroke="#22D3EE" stroke-width="2" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    lines.append(
        f'<text x="68" y="36" font-family="{SANS}" font-size="15" '
        f'font-weight="700" fill="{TEXT_PRIMARY}" letter-spacing="0.3">'
        f"Activity Graph</text>"
    )
    lines.append(
        f'<text x="68" y="50" font-family="{SANS}" font-size="10.5" '
        f'fill="{TEXT_MUTED}" letter-spacing="0.2">Daily contribution analytics</text>'
    )

    # Date range badge
    if display_days:
        start_date = display_days[0][0].strftime("%b %d")
        end_date = display_days[-1][0].strftime("%b %d, %Y")
        range_text = f"{start_date} – {end_date}"
    else:
        range_text = "No data"
    lines.append(
        f'<rect x="720" y="24" width="230" height="30" rx="8" '
        f'fill="{BORDER}" stroke="{GRID}" stroke-width="0.75"/>'
    )
    lines.append(
        f'<text x="835" y="43" text-anchor="middle" font-family="{SANS}" '
        f'font-size="11" font-weight="500" fill="{TEXT_SECONDARY}" '
        f'letter-spacing="0.3">{esc(range_text)}</text>'
    )

    # Grid lines (horizontal)
    lines.append(f'<g opacity="0.35" stroke="{GRID}" stroke-width="0.5">')
    for i in range(y_ticks + 1):
        y = CHART_BOTTOM - (i * y_step / y_max) * CHART_H
        lines.append(
            f'<line x1="{CHART_LEFT}" y1="{y:.1f}" x2="{CHART_RIGHT}" y2="{y:.1f}"/>'
        )
    lines.append("</g>")

    # Grid lines (vertical) — weekly
    lines.append(
        f'<g opacity="0.2" stroke="{GRID}" stroke-width="0.5" stroke-dasharray="4 4">'
    )
    for i in range(0, n, 7):
        x = CHART_LEFT + (i / max(n - 1, 1)) * CHART_W
        lines.append(
            f'<line x1="{x:.1f}" y1="{CHART_TOP}" x2="{x:.1f}" y2="{CHART_BOTTOM}"/>'
        )
    lines.append("</g>")

    # Y-axis labels
    for i in range(y_ticks + 1):
        val = i * y_step
        y = CHART_BOTTOM - (i * y_step / y_max) * CHART_H
        lines.append(
            f'<text x="{CHART_LEFT - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="{SANS}" font-size="10" fill="{TEXT_DIM}">{val}</text>'
        )

    # X-axis labels (show every 7th day or key labels)
    label_positions = []
    # Always show first, last, and every 7th day
    for i in range(0, n, 7):
        label_positions.append(i)
    if (n - 1) not in label_positions:
        label_positions.append(n - 1)

    for i in label_positions:
        x = CHART_LEFT + (i / max(n - 1, 1)) * CHART_W
        date_obj = display_days[i][0]
        day_name = date_obj.strftime("%a")
        day_num = date_obj.strftime("%d")
        lines.append(
            f'<text x="{x:.1f}" y="{CHART_BOTTOM + 16}" text-anchor="middle" '
            f'font-family="{SANS}" font-size="10" fill="{TEXT_DIM}">{day_name}</text>'
        )
        lines.append(
            f'<text x="{x:.1f}" y="{CHART_BOTTOM + 28}" text-anchor="middle" '
            f'font-family="{SANS}" font-size="9" fill="{TEXT_MUTED}">{day_num}</text>'
        )

    # Area fill path
    area_path = smooth_path(points)
    area_path += f" L{points[-1][0]:.1f},{CHART_BOTTOM} L{points[0][0]:.1f},{CHART_BOTTOM} Z"
    lines.append(
        f'<path clip-path="url(#chartClip)" d="{area_path}" fill="url(#areaGrad)"/>'
    )

    # Glow line (wider, blurred)
    main_path = smooth_path(points)
    lines.append(
        f'<path clip-path="url(#chartClip)" d="{main_path}" fill="none" '
        f'stroke="url(#glowGrad)" stroke-width="5" stroke-linecap="round" opacity="0.5"/>'
    )

    # Main line
    lines.append(
        f'<path clip-path="url(#chartClip)" d="{main_path}" fill="none" '
        f'stroke="url(#lineGrad)" stroke-width="2.5" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
    )

    # Data points — active (above zero) with glow
    lines.append('<g filter="url(#glow)">')
    for i, (x, y) in enumerate(points):
        if counts[i] > 0:
            # Color cycles through accent palette
            colors = ["#22D3EE", "#3B82F6", "#8B5CF6", "#EC4899"]
            color = colors[i % len(colors)]
            r = 4.5 if counts[i] >= max_val * 0.5 else 3.5
            lines.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}"/>'
            )
    lines.append("</g>")

    # Inactive points (zero contributions)
    lines.append('<g opacity="0.4">')
    for i, (x, y) in enumerate(points):
        if counts[i] == 0:
            lines.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{TEXT_MUTED}"/>'
            )
    lines.append("</g>")

    # Tooltip-style value labels on hover (hidden by default, CSS hover)
    for i, (x, y) in enumerate(points):
        if counts[i] > 0:
            lines.append(
                f'<title>{display_days[i][0].strftime("%b %d, %Y")} — {counts[i]} contribution{"s" if counts[i] != 1 else ""}</title>'
            )

    # --- Stat cards (real data) ---
    stat_y = CHART_BOTTOM + 48
    stat_h = 60
    card_gap = 12
    card_width = (CARD_W - 2 * CHART_LEFT - 3 * card_gap) / 4

    stat_data = [
        ("Total Contributions", fmt(stats["total"]), "#22D3EE", 1),
        ("Current Streak", f"{stats['current_streak']}d", "#3B82F6", 2),
        ("Longest Streak", f"{stats['longest_streak']}d", "#8B5CF6", 3),
        ("Active Days", f"{stats['active_days']}/{len(display_days)}", "#EC4899", 4),
    ]

    for idx, (label, value, color, icon_idx) in enumerate(stat_data):
        sx = CHART_LEFT + idx * (card_width + card_gap)
        sy = stat_y

        # Card background
        lines.append(
            f'<rect x="{sx:.1f}" y="{sy}" width="{card_width:.1f}" height="{stat_h}" '
            f'rx="12" fill="url(#stat{icon_idx})" stroke="{BORDER}" stroke-width="0.75"/>'
        )

        # Icon background
        ix = sx + 16
        iy = sy + 14
        lines.append(
            f'<rect x="{ix}" y="{iy}" width="32" height="32" rx="8" fill="url(#ic{icon_idx})"/>'
        )

        # Icon path (simple shape per stat)
        icons = {
            1: f'<path d="M{ix+8} {iy+16}l4 4 8-8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
            2: f'<path d="M{ix+8} {iy+20}l4-8h4l4 8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{ix+16}" cy="{iy+12}" r="2" fill="{color}"/>',
            3: f'<path d="M{ix+8} {iy+16}l4 4 8-8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M{ix+8} {iy+22}l4 4 8-8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>',
            4: f'<circle cx="{ix+16}" cy="{iy+16}" r="6" stroke="{color}" stroke-width="1.8" fill="none"/>'
            f'<circle cx="{ix+16}" cy="{iy+16}" r="2" fill="{color}"/>',
        }
        lines.append(icons[icon_idx])

        # Value text
        vx = ix + 44
        vy = sy + 30
        lines.append(
            f'<text x="{vx}" y="{vy}" font-family="{MONO}" font-size="18" '
            f'font-weight="800" fill="{TEXT_PRIMARY}">{esc(value)}</text>'
        )

        # Label text
        lx = sx + 16
        ly = sy + stat_h - 10
        lines.append(
            f'<text x="{lx}" y="{ly}" font-family="{SANS}" font-size="10.5" '
            f'fill="{TEXT_MUTED}" letter-spacing="0.2">{esc(label)}</text>'
        )

    # Footer
    lines.append(
        f'<text x="48" y="{total_h - 10}" font-family="{SANS}" font-size="10.5" '
        f'fill="{TEXT_MUTED}">github.com/{esc(username)} • Updated {datetime.now(timezone.utc).strftime("%b %d, %Y")}</text>'
    )

    # Source attribution
    lines.append(
        f'<text x="{CARD_W - 32}" y="{total_h - 10}" text-anchor="end" '
        f'font-family="{SANS}" font-size="10" fill="{TEXT_DIM}">Data: GitHub GraphQL API</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <username> <output_dir>")
        sys.exit(1)

    username = sys.argv[1]
    output_dir = sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN", "")

    if not token:
        print("Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Fetching contribution data for {username}...")
    days, total_year = fetch_contribution_data(username, token)
    print(f"  Fetched {len(days)} days of data, {total_year} total contributions this year")

    stats = compute_stats(days)
    print(f"  Stats: total={stats['total']}, current_streak={stats['current_streak']}, "
          f"longest_streak={stats['longest_streak']}, active_days={stats['active_days']}")

    svg = generate_svg(days, stats, username)
    outfile = os.path.join(output_dir, "activity.svg")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"  Generated: {outfile}")
    print(f"  SVG size: {len(svg)} bytes")
    print("Done!")


if __name__ == "__main__":
    main()
