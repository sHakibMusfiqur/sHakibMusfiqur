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

---

## 3. Featured Projects

Each project card links two buttons. Point them at your real repositories:

- GitHub cell: Gold standard `https://github.com/YOUR_USER/REPO`
- Live demo cell: deployment URL, e.g. `https://REPO.vercel.app`

Edit the `<a href="...">` anchors inside **Featured Projects** in `README.md`.

---

## 4. Contact Links

Replace the mailto and profile links in the **Contact** section:

```
mailto:your-email@example.com
https://github.com/YOUR_USER
```

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

All dynamic cards support theming via query parameters:

| Service | Host |
| --- | --- |
| Stats & Top Languages | `github-readme-stats.vercel.app` |
| Streak | `streak-stats.demolab.com` |
| Trophy | `github-profile-trophy.vercel.app` |
| Activity Graph | `github-readme-activity-graph.vercel.app` |
| Typing animation | `readme-typing-svg.demolab.com` |

Change any color by editing params like `title_color=C41E3A`,
`text_color=334155`, `bg_color=ffffff`. Refer to each service's own README for
the full list of options.

---

## 7. Project Structure

```
ShakibMusfiqur/
├── README.md                 # The profile page (HTML + Markdown)
├── LICENSE                   # MIT license
├── assets/
│   ├── banner.svg            # Hero banner
│   ├── divider.svg           # Section divider
│   ├── footer.svg            # Page footer
│   ├── profile-bg.svg        # About section background
│   ├── avatar-frame.svg      # Avatar orbit ring
│   ├── project-card.svg      # Featured project illustration
│   ├── icons/                # Custom line icons
│   └── screenshots/          # Add profile screenshots here
├── .github/workflows/
│   └── snake.yml             # Daily contribution snake job
└── docs/
    └── customization.md      # You are here
```

---

## 8. Making It Truly Yours

1. `git push origin main` — the profile becomes live.
2. Watch the **Actions** tab run the snake job once.
3. Replace contact + project URLs.
4. Swap the SVG palette in `assets/` if you want a different accent.
5. Add a screenshot of your rendered profile to `assets/screenshots/`.

---

> Tip: GitHub strips inline CSS for security. This template deliberately relies on
> **HTML tables, aligned images, and server-rendered SVG badges** — all of which
> render cleanly and reliably on github.com.