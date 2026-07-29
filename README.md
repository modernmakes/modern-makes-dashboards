# Modern Makes — Dashboards

Internal infrastructure for Modern Makes: two lightweight, static, fetch-JSON dashboards served via GitHub Pages — **Trend Scan** (`/trend-scan/`, daily-refreshed Reddit/GitHub/YouTube/manufacturer-feed signal ranking) and the **Content Dashboard** (`/content-dashboard/`, a snapshot of the editorial pipeline). This repo is deliberately **unlisted**: it is not linked from modernmakes.github.io, not submitted to search engines, and carries no `robots.txt`/sitemap entries anywhere. It exists solely as a URL Matt checks directly.

**No API tokens are ever committed here or added as GitHub Actions secrets** — not Airtable, not anything else. The Trend Scan workflow uses only the built-in, auto-issued `GITHUB_TOKEN` to commit its own data back to this repo. The Airtable push (`push_to_airtable.py`) is intentionally excluded from this repo and remains a manual, local-only step run from the original `research/` folder in Cowork — it is not duplicated or automated here.

## Trend Scan

`trend-scan/toolbox/` holds the fetchers (`fetch_reddit.py`, `fetch_github.py`, `fetch_youtube.py`, `fetch_manufacturer_news.py`) and `score_signals.py`, run daily by `.github/workflows/trend-scan.yml` (also triggerable manually via `workflow_dispatch`). Each fetcher writes to `trend-scan/data/raw/`; `score_signals.py` reads that history and writes `trend-scan/data/trend-signals.json` (+ a `.js` fallback for `file://` opens). The workflow commits and pushes any changed files under `trend-scan/data/` using `GITHUB_TOKEN`. `trend-scan/inputs/sources.json` configures the tracked subreddits, GitHub repos, YouTube channels, and manufacturer feeds.

## Content Dashboard

`content-dashboard/index.html` fetches `content-dashboard/data/tracker.json` (same pattern as Trend Scan, `.js` fallback included) and renders pipeline stats, the status board, pillar coverage, and the strategy snapshot. **There is no automation for this one yet** — `tracker.json` is a manual snapshot parsed from `Content Tracker.md` and `Strategy.md` in the claude-obsidian vault. After editing those files, regenerating `tracker.json` (and its `.js` fallback) is a manual step for now. A future upgrade could wire a cross-repo GitHub Action from the `claude-obsidian` vault via a scoped PAT, if Matt wants that later.

## Publishing

Matt publishes this repo manually from GitHub Desktop, then enables Pages himself (Settings → Pages → source: `main` branch, root) — that toggle isn't git-automatable.
