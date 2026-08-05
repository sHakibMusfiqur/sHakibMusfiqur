#!/usr/bin/env python3
"""
GitHub Activity Graph SVG Generator
====================================
Fetches real contribution data from the GitHub GraphQL API and generates
a premium dark-theme SVG analytics card with a smooth line chart.

No external dependencies -- Python 3.8+ stdlib only.

Usage:
    GITHUB_TOKEN=ghp_xxx python3 generate_activity.py <username> <output_dir>

Output:
    <output_dir>/activity.svg

Data sources (in priority order):
    1. GitHub GraphQL API: contributionsCollection.contributionCalendar
    2. GitHub REST API: /users/{user}/events (fallback)
"""

import json
import math
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
CARD = "#111827"
BORDER = "#1F2937"
GRID = "#374151"
TEXT_PRIMARY = "#F9FAFB"
TEXT_SECONDARY = "#D1D5DB"
TEXT_MUTED = "#6B7280"
TEXT_DIM = "#4B5563"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Consolas, monospace"

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(url, token, accept="application/vnd.github+json"):
    """Make an authenticated GET request to the GitHub API."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "activity-graph-action")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post(url, token, data, accept="application/vnd.github+json"):
    """Make an authenticated POST request to the GitHub API."""
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "activity-graph-action")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

# GraphQL query -- current year (no deprecated from/to parameters)
GRAPHQL_QUERY_CURRENT_YEAR = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
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

def fetch_via_graphql(username, token):
    """Fetch contribution data via GraphQL (current year)."""
    try:
        resp = api_post(
            "https://api.github.com/graphql",
            token,
            data={"query": GRAPHQL_QUERY_CURRENT_YEAR, "variables": {"login": username}},
        )
        if "errors" in resp:
            print(f"  GraphQL errors: {resp['errors']}")
            return None

        user = (resp.get("data") or {}).get("user")
        if not user:
            print(f"  GraphQL: user not found for '{username}'")
            return None

        cal = user["contributionsCollection"]["contributionCalendar"]
        total_year = cal["totalContributions"]

        days = []
        for week in cal["weeks"]:
            for day in week["contributionDays"]:
                dt = datetime.strptime(day["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days.append((dt, day["contributionCount"]))
        days.sort(key=lambda x: x[0])

        print(f"  GraphQL: {len(days)} days, {total_year} total contributions")
        return days, total_year
    except Exception as e:
        print(f"  GraphQL failed: {e}")
        return None


def fetch_via_rest(username, token):
    """Fallback: fetch contribution data from public events (last 90 days)."""
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=90)

        # Collect push + issues + PR events
        events = []
        page = 1
        while page <= 5:  # max 5 pages
            url = f"https://api.github.com/users/{username}/events/public?per_page=100&page={page}"
            try:
                page_events = api_get(url, token)
            except urllib.error.HTTPError:
                break
            if not page_events:
                break
            for ev in page_events:
                created = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
                if created < cutoff:
                    break
                if ev["type"] in ("PushEvent", "IssuesEvent", "PullRequestEvent",
                                  "PullRequestReviewEvent", "CommitCommentEvent",
                                  "CreateEvent", "DeleteEvent", "ReleaseEvent"):
                    events.append(created)
            if page_events and datetime.fromisoformat(page_events[-1]["created_at"].replace("Z", "+00:00")) < cutoff:
                break
            page += 1

        # Aggregate by day
        day_counts = {}
        for dt in events:
            key = dt.strftime("%Y-%m-%d")
            day_counts[key] = day_counts.get(key, 0) + 1

        # Build day list for the last 90 days
        days = []
        for i in range(89, -1, -1):
            dt = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            key = dt.strftime("%Y-%m-%d")
            days.append((dt, day_counts.get(key, 0)))

        total_year = sum(c for _, c in days)
        print(f"  REST fallback: {len(days)} days, {total_year} contributions (90-day window)")
        return days, total_year
    except Exception as e:
        print(f"  REST fallback failed: {e}")
        return None


def fetch_contribution_data(username, token):
    """Fetch contribution data. Tries GraphQL first, then REST fallback."""
    result = fetch_via_graphql(username, token)
    if result:
        return result

    print("  Trying REST API fallback...")
    result = fetch_via_rest(username, token)
    if result:
        return result

    # Last resort: return empty data so the SVG still renders
    print("  All API attempts failed. Generating SVG with zero data.")
    now = datetime.now(timezone.utc)
    days = [((now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0), 0)
            for i in range(89, -1, -1)]
    return days, 0


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def compute_stats(days):
    """Compute real stats from contribution data."""
    if not days:
        return {"total": 0, "current_streak": 0, "longest_streak": 0,
                "active_days": 0, "max_daily": 0, "avg_daily": 0.0}

    counts = [c for _, c in days]
    total = sum(counts)
    active = sum(1 for c in counts if c > 0)
    max_daily = max(counts) if counts else 0
    avg_daily = total / len(counts) if counts else 0.0

    current_streak = 0
    for count in reversed(counts):
        if count > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    streak = 0
    for count in counts:
        if count > 0:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0

    return {"total": total, "current_streak": current_streak,
            "longest_streak": longest_streak, "active_days": active,
            "max_daily": max_daily, "avg_daily": avg_daily}


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def fmt(n):
    return f"{int(n):,}"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def smooth_path(points):
    """Catmull-Rom to cubic bezier SVG path."""
    if len(points) < 2:
        return ""
    n = len(points)
    parts = [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
    for i in range(n - 1):
        p0 = points[max(i - 1, 0)]
        p1 = points[i]
        p2 = points[min(i + 1, n - 1)]
        p3 = points[min(i + 2, n - 1)]
        t = 6.0
        cp1x = p1[0] + (p2[0] - p0[0]) / t
        cp1y = p1[1] + (p2[1] - p0[1]) / t
        cp2x = p2[0] - (p3[0] - p1[0]) / t
        cp2y = p2[1] - (p3[1] - p1[1]) / t
        parts.append(f"C{cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {p2[0]:.1f},{p2[1]:.1f}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# SVG generation
# ---------------------------------------------------------------------------

def generate_svg(days, stats, username):
    """Generate the complete SVG from real data."""
    CARD_W = 980
    CHART_LEFT = 80
    CHART_RIGHT = 940
    CHART_TOP = 80
    CHART_BOTTOM = 266
    CHART_W = CHART_RIGHT - CHART_LEFT
    CHART_H = CHART_BOTTOM - CHART_TOP

    # Display last 30 days
    display_days = days[-30:] if len(days) >= 30 else days
    n = len(display_days)
    counts = [c for _, c in display_days]
    max_val = max(counts) if counts else 1
    if max_val == 0:
        max_val = 1

    y_ticks = 5
    y_step = math.ceil(max_val / y_ticks)
    y_max = y_step * y_ticks
    if y_max == 0:
        y_max = y_ticks

    def to_xy(i, val):
        x = CHART_LEFT + (i / max(n - 1, 1)) * CHART_W
        y = CHART_BOTTOM - (val / y_max) * CHART_H
        return (x, y)

    points = [to_xy(i, c) for i, c in enumerate(counts)]
    total_h = 380
    out = []

    # Opening tag
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {total_h}" '
        f'width="{CARD_W}" height="{total_h}" role="img" '
        f'aria-label="Activity Graph — GitHub contribution analytics for {esc(username)}">'
    )

    # Defs
    out.append("<defs>")
    for gid, stops in [
        ("lineGrad", [("0%", "#22D3EE"), ("33%", "#3B82F6"), ("66%", "#8B5CF6"), ("100%", "#EC4899")]),
        ("areaGrad", [("0%", "#22D3EE", 0.18), ("40%", "#3B82F6", 0.10), ("70%", "#8B5CF6", 0.04), ("100%", "#EC4899", 0)]),
        ("glowGrad", [("0%", "#22D3EE", 0.35), ("33%", "#3B82F6", 0.30), ("66%", "#8B5CF6", 0.25), ("100%", "#EC4899", 0.20)]),
    ]:
        x1, y1, x2, y2 = (0, 0, 1, 0) if gid != "areaGrad" else (0, 0, 0, 1)
        out.append(f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">')
        for s in stops:
            offset, color = s[0], s[1]
            opacity = f' stop-opacity="{s[2]}"' if len(s) > 2 else ""
            out.append(f'<stop offset="{offset}" stop-color="{color}"{opacity}/>')
        out.append("</linearGradient>")

    out.append('<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
               '<feGaussianBlur stdDeviation="3" result="blur"/>'
               '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    out.append('<filter id="softShadow" x="-10%" y="-10%" width="120%" height="130%">'
               '<feDropShadow dx="0" dy="4" stdDeviation="12" flood-color="#000" flood-opacity="0.35"/></filter>')
    out.append(f'<clipPath id="chartClip"><rect x="{CHART_LEFT}" y="{CHART_TOP}" width="{CHART_W}" height="{CHART_H}"/></clipPath>')

    for i, color in enumerate(["#22D3EE", "#3B82F6", "#8B5CF6", "#EC4899"], 1):
        out.append(f'<linearGradient id="ic{i}" x1="0" y1="0" x2="1" y2="1">'
                   f'<stop offset="0%" stop-color="{color}" stop-opacity="0.22"/>'
                   f'<stop offset="100%" stop-color="{color}" stop-opacity="0.08"/></linearGradient>')
        out.append(f'<linearGradient id="stat{i}" x1="0" y1="0" x2="1" y2="1">'
                   f'<stop offset="0%" stop-color="{color}" stop-opacity="0.15"/>'
                   f'<stop offset="100%" stop-color="{color}" stop-opacity="0.05"/></linearGradient>')
    out.append("</defs>")

    # Card
    out.append(f'<rect x="1" y="1" width="{CARD_W-2}" height="{total_h-2}" rx="20" fill="{CARD}" stroke="{BORDER}" stroke-width="1" filter="url(#softShadow)"/>')
    out.append(f'<rect x="1" y="1" width="{CARD_W-2}" height="1" rx="0.5" fill="url(#lineGrad)" opacity="0.5"/>')

    # Header
    out.append('<rect x="32" y="26" width="28" height="28" rx="8" fill="#22D3EE" fill-opacity="0.15"/>')
    out.append('<path d="M40 36l4 4 8-8" stroke="#22D3EE" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    out.append(f'<text x="68" y="36" font-family="{SANS}" font-size="15" font-weight="700" fill="{TEXT_PRIMARY}" letter-spacing="0.3">Activity Graph</text>')
    out.append(f'<text x="68" y="50" font-family="{SANS}" font-size="10.5" fill="{TEXT_MUTED}" letter-spacing="0.2">Daily contribution analytics</text>')

    # Date range badge
    if display_days:
        start_date = display_days[0][0].strftime("%b %d")
        end_date = display_days[-1][0].strftime("%b %d, %Y")
        range_text = f"{start_date} \u2013 {end_date}"
    else:
        range_text = "No data"
    out.append(f'<rect x="720" y="24" width="230" height="30" rx="8" fill="{BORDER}" stroke="{GRID}" stroke-width="0.75"/>')
    out.append(f'<text x="835" y="43" text-anchor="middle" font-family="{SANS}" font-size="11" font-weight="500" fill="{TEXT_SECONDARY}" letter-spacing="0.3">{esc(range_text)}</text>')

    # Grid
    out.append(f'<g opacity="0.35" stroke="{GRID}" stroke-width="0.5">')
    for i in range(y_ticks + 1):
        y = CHART_BOTTOM - (i * y_step / y_max) * CHART_H
        out.append(f'<line x1="{CHART_LEFT}" y1="{y:.1f}" x2="{CHART_RIGHT}" y2="{y:.1f}"/>')
    out.append("</g>")
    out.append(f'<g opacity="0.2" stroke="{GRID}" stroke-width="0.5" stroke-dasharray="4 4">')
    for i in range(0, n, 7):
        x = CHART_LEFT + (i / max(n - 1, 1)) * CHART_W
        out.append(f'<line x1="{x:.1f}" y1="{CHART_TOP}" x2="{x:.1f}" y2="{CHART_BOTTOM}"/>')
    out.append("</g>")

    # Y-axis labels
    for i in range(y_ticks + 1):
        val = i * y_step
        y = CHART_BOTTOM - (i * y_step / y_max) * CHART_H
        out.append(f'<text x="{CHART_LEFT - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="{SANS}" font-size="10" fill="{TEXT_DIM}">{val}</text>')

    # X-axis labels
    label_positions = list(range(0, n, 7))
    if (n - 1) not in label_positions:
        label_positions.append(n - 1)
    for i in label_positions:
        x = CHART_LEFT + (i / max(n - 1, 1)) * CHART_W
        d = display_days[i][0]
        out.append(f'<text x="{x:.1f}" y="{CHART_BOTTOM + 16}" text-anchor="middle" font-family="{SANS}" font-size="10" fill="{TEXT_DIM}">{d.strftime("%a")}</text>')
        out.append(f'<text x="{x:.1f}" y="{CHART_BOTTOM + 28}" text-anchor="middle" font-family="{SANS}" font-size="9" fill="{TEXT_MUTED}">{d.strftime("%d")}</text>')

    # Area fill
    area_path = smooth_path(points) + f" L{points[-1][0]:.1f},{CHART_BOTTOM} L{points[0][0]:.1f},{CHART_BOTTOM} Z"
    out.append(f'<path clip-path="url(#chartClip)" d="{area_path}" fill="url(#areaGrad)"/>')

    # Glow line
    main_path = smooth_path(points)
    out.append(f'<path clip-path="url(#chartClip)" d="{main_path}" fill="none" stroke="url(#glowGrad)" stroke-width="5" stroke-linecap="round" opacity="0.5"/>')

    # Main line
    out.append(f'<path clip-path="url(#chartClip)" d="{main_path}" fill="none" stroke="url(#lineGrad)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')

    # Data points
    colors = ["#22D3EE", "#3B82F6", "#8B5CF6", "#EC4899"]
    out.append('<g filter="url(#glow)">')
    for i, (x, y) in enumerate(points):
        if counts[i] > 0:
            c = colors[i % len(colors)]
            r = 4.5 if counts[i] >= max_val * 0.5 else 3.5
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}"/>')
    out.append("</g>")

    out.append('<g opacity="0.4">')
    for i, (x, y) in enumerate(points):
        if counts[i] == 0:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{TEXT_MUTED}"/>')
    out.append("</g>")

    # Stat cards
    stat_y = CHART_BOTTOM + 48
    stat_h = 60
    card_gap = 12
    card_width = (CARD_W - 2 * CHART_LEFT - 3 * card_gap) / 4

    stat_data = [
        ("Total Contributions", fmt(stats["total"]), 1),
        ("Current Streak", f"{stats['current_streak']}d", 2),
        ("Longest Streak", f"{stats['longest_streak']}d", 3),
        ("Active Days", f"{stats['active_days']}/{len(display_days)}", 4),
    ]

    for idx, (label, value, icon_idx) in enumerate(stat_data):
        sx = CHART_LEFT + idx * (card_width + card_gap)
        sy = stat_y
        color = ["#22D3EE", "#3B82F6", "#8B5CF6", "#EC4899"][idx]

        out.append(f'<rect x="{sx:.1f}" y="{sy}" width="{card_width:.1f}" height="{stat_h}" rx="12" fill="url(#stat{icon_idx})" stroke="{BORDER}" stroke-width="0.75"/>')

        ix, iy = sx + 16, sy + 14
        out.append(f'<rect x="{ix}" y="{iy}" width="32" height="32" rx="8" fill="url(#ic{icon_idx})"/>')

        icons = {
            1: f'<path d="M{ix+8} {iy+16}l4 4 8-8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
            2: f'<path d="M{ix+8} {iy+20}l4-8h4l4 8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/><circle cx="{ix+16}" cy="{iy+12}" r="2" fill="{color}"/>',
            3: f'<path d="M{ix+8} {iy+16}l4 4 8-8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M{ix+8} {iy+22}l4 4 8-8" stroke="{color}" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>',
            4: f'<circle cx="{ix+16}" cy="{iy+16}" r="6" stroke="{color}" stroke-width="1.8" fill="none"/><circle cx="{ix+16}" cy="{iy+16}" r="2" fill="{color}"/>',
        }
        out.append(icons[icon_idx])
        out.append(f'<text x="{ix+44}" y="{sy+30}" font-family="{MONO}" font-size="18" font-weight="800" fill="{TEXT_PRIMARY}">{esc(value)}</text>')
        out.append(f'<text x="{sx+16}" y="{sy+stat_h-10}" font-family="{SANS}" font-size="10.5" fill="{TEXT_MUTED}" letter-spacing="0.2">{esc(label)}</text>')

    # Footer
    out.append(f'<text x="48" y="{total_h - 10}" font-family="{SANS}" font-size="10.5" fill="{TEXT_MUTED}">github.com/{esc(username)} \u2022 Updated {datetime.now(timezone.utc).strftime("%b %d, %Y")}</text>')
    out.append(f'<text x="{CARD_W - 32}" y="{total_h - 10}" text-anchor="end" font-family="{SANS}" font-size="10" fill="{TEXT_DIM}">Data: GitHub API</text>')

    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
    print(f"  Got {len(days)} days of data")

    stats = compute_stats(days)
    print(f"  Stats: total={stats['total']}, streak={stats['current_streak']}, "
          f"longest={stats['longest_streak']}, active={stats['active_days']}")

    svg = generate_svg(days, stats, username)
    outfile = os.path.join(output_dir, "activity.svg")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"  Generated: {outfile} ({len(svg)} bytes)")
    print("Done!")


if __name__ == "__main__":
    main()
