# Customization Guide

Everything you need to make this profile fully your own. The whole design is driven
by a **white + soft-gray + black** palette with a **premium red accent (`#C41E3A`)**.

---

## 1. Brand Colors

| Token | Hex | Usage |
| --- | --- | --- |
| Accent Red | `#C41E3A` | Primary accent, buttons, active states |
| Red Dark | `#8E1227` | Accent gradients, hover |
| Red Bright | `#E31E45` | Gradient start highlight |
| Ink (Black) | `#0B1220` | Headings, primary text |
| Body Text | `#334155` | Paragraphs |
| Muted Text | `#64748B` | Secondary / captions |
| Border | `#E2E8F0` | Hairlines, card strokes |
| Soft Surface | `#F8FAFC` | Card fills, section breathers |

When customizing the SVG artwork (`banner.svg`, `footer.svg`, etc.),
edit colors inline by targeting the gradient/hex values above.

---

## 2. GitHub Username

The wordmark, stats cards, snake, trophy and badges all reference a username.
Search the repo for the placeholder and replace everywhere:

```
sHakibMusfiqur
```

Files that reference it:

- `README.md` — all card/image URLs
- `.github/workflows/snake.yml` — reads `github.repository_owner` automatically
  (no change needed)
- `.github/workflows/stats.yml` — reads `github.repository_owner` automatically
  (no change needed)

---

## 3. Featured Projects

The six project cards currently show **Coming Soon** badges — they don't point at
any live repositories yet. When you have real repos, replace each badge in
**Featured Projects** in `README.md` with a button anchor:

- GitHub cell: `https://github.com/YOUR_USER/REPO`
- Live demo cell: deployment URL, e.g. `https://REPO.vercel.app`

```html
<a href="https://github.com/YOUR_USER/REPO">
  <img src="https://img.shields.io/badge/View%20Code-0B1220?style=flat-square" alt="View Code"/>
</a>
```

---

## 4. Contact Links

Replace the profile links in the **Contact** section:

```
https://github.com/YOUR_USER
https://github.com/YOUR_USER?tab=repositories
```

There is no public email on the profile by design; add one only if you want it.

---

## 5. The Contribution Snake

The workflow at `.github/workflows/snake.yml` runs **daily** (and on every push
to `main`) to regenerate your contribution snake.

- Output files live on the `output` branch.
- They are rendered from:

```
https://raw.githubusercontent.com/sHakibMusfiqur/sHakibMusfiqur/output/github-contribution-grid-snake.svg
```

It updates **automatically** — no action required after the first push.
You can also trigger it manually from the **Actions** tab.

> Requires `contents: write` permission (already set) and the default
> `GITHUB_TOKEN`. No personal token needed.

---

## 6. Statistics Cards

**The GitHub stats dashboard is self-hosted** by `.github/workflows/stats.yml`.
The job queries the GitHub API directly (REST search for stars/commits/PRs/issues,
GraphQL for contributions and languages) and renders a single dark analytics-panel
card, then pushes it to the `stats` branch. It renders from:

```
https://raw.githubusercontent.com/sHakibMusfiqur/sHakibMusfiqur/stats/stats.svg
```

The card is theme-independent dark (`#0D1117`) by design, with red `#C41E3A`
and violet `#7C3AED` accents. It shows five metrics on the left (stars, commits,
pull requests, issues, contributions this year) with a circular language
indicator, and animated language bars on the right.

Trigger it from the **Actions** tab (workflow_dispatch) or let it run on the
daily schedule.

Remaining third-party services:

| Service | Host |
| --- | --- |
| Streak | `streak-stats.demolab.com` |
| Activity Graph | `github-readme-activity-graph.vercel.app` |
| Typing animation | `readme-typing-svg.demolab.com` |
| Tech stack icons | `skillicons.dev` |
| Badges | `img.shields.io` |

The trophies widget is replaced by a static `assets/achievements.svg` so no
external trophy service is needed.

---

## 7. Project Structure

```
ShakibMusfiqur/
├── README.md                 # The profile page (HTML + Markdown)
├── LICENSE                   # MIT license
├── assets/
│   ├── banner.svg            # Hero banner (light)
│   ├── banner-dark.svg       # Hero banner (dark)
│   ├── divider.svg           # Section divider
│   ├── footer.svg            # Page footer (light)
│   ├── footer-dark.svg       # Page footer (dark)
│   ├── profile-bg.svg        # About section background (light)
│   ├── profile-bg-dark.svg   # About section background (dark)
│   ├── achievements.svg      # Static achievements card
│   ├── avatar-frame.svg      # Avatar orbit ring
│   ├── project-card.svg      # Featured project illustration
│   ├── icons/                # Custom line icons
│   └── screenshots/          # Add profile screenshots here
├── .github/workflows/
│   ├── snake.yml             # Daily contribution snake job
│   └── stats.yml             # Self-hosted stats + top-langs cards
└── docs/
    └── customization.md      # You are here
```

---

## 8. Making It Truly Yours

1. `git push origin main` — the profile becomes live.
2. Watch the **Actions** tab run the snake and stats jobs once (this creates the
   `output` and `stats` branches that the cards load from).
3. Replace contact + project URLs.
4. Swap the SVG palette in `assets/` if you want a different accent.
5. Add a screenshot of your rendered profile to `assets/screenshots/`.

---

> Tip: GitHub strips inline CSS for security. This template deliberately relies on
> **HTML tables, aligned images, and server-rendered SVG badges** — all of which
> render cleanly and reliably on github.com.