"""Rank the scored raw signals into data/trend-signals.json.

Only GitHub and YouTube are scored — they carry engagement numbers (stars, views).
Scoring has two modes, chosen per item depending on how much history exists in
data/raw/:

  baseline-spike  Enough prior days for this entity, so the item is scored on how
                  far today's number sits above its own 30-day baseline (z-score).
                  A repo dead on its own star-velocity baseline is not a signal.
  raw-engagement  First runs, or a newly added source. Ranked on raw engagement,
                  normalised within its own source so a 15k-star repo does not
                  permanently outrank every YouTube video.

Both modes emit the same 0-100 score so the dashboard can rank one flat list.

Reddit is deliberately NOT scored. Its RSS feed carries no score or comment count
(see fetch_reddit.py), so there is nothing to rank on. Reddit threads are passed
through untouched as a separate `recent_threads` array — context, not competition.
"""

import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_JSON = ROOT / "data" / "trend-signals.json"
OUT_JS = ROOT / "data" / "trend-signals.js"

BASELINE_DAYS = 30
MIN_BASELINE_SAMPLES = 5      # below this, a z-score is noise dressed up as maths
YOUTUBE_RECENT_DAYS = 30      # older videos are catalogue, not trend. Tuned to the
                              # configured channels' ~monthly cadence: at 21 days
                              # a run surfaced a single video.
TOP_N = 60


# ── helpers ─────────────────────────────────────────────────────────────────

def load_raw() -> dict:
    """{source: {date: payload}} for every data/raw/<source>-<date>.json."""
    out = {}
    for path in sorted(RAW_DIR.glob("*.json")):
        stem = path.stem
        if "-" not in stem:
            continue
        source, _, date = stem.partition("-")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[score] skipping unreadable {path.name}")
            continue
        out.setdefault(source, {})[date] = payload
    return out


def days_between(a: str, b: str) -> int:
    fmt = "%Y-%m-%d"
    return abs((datetime.strptime(a, fmt) - datetime.strptime(b, fmt)).days)


def zscore(current: float, baseline: list) -> float | None:
    """None when the baseline is too thin to mean anything."""
    if len(baseline) < MIN_BASELINE_SAMPLES:
        return None
    mean = statistics.mean(baseline)
    stdev = statistics.pstdev(baseline)
    if stdev < 1e-9:
        # Flat baseline: any move is notable, but cap it rather than divide by ~0.
        return 0.0 if current <= mean else 3.0
    return (current - mean) / stdev


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def spike_to_score(z: float) -> float:
    """z=0 (dead on baseline) -> 50. z=+2 -> ~74. z=+4 -> ~98."""
    return round(clamp(50 + 12 * z), 1)


def normalise(value: float, peak: float) -> float:
    if peak <= 0:
        return 0.0
    return round(clamp(100 * value / peak), 1)


def slug(text: str) -> str:
    """Lowercase, keep alphanumerics and dots, collapse the rest to single dashes.

    Dots are kept so a release tag like v2.4.2 survives intact in a Signal Key.
    """
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9.]+", "-", text)
    return text.strip("-")


# ── reddit (unscored, context only) ──────────────────────────────────────────

def collect_reddit_threads(by_date: dict, latest: str) -> list:
    """Pass RSS threads through untouched — no score, no rank. Newest first."""
    today = by_date.get(latest, {}).get("items", [])
    threads = []
    for post in today:
        published = post.get("published") or ""
        threads.append(
            {
                "title": post.get("title"),
                "subreddit": post.get("subreddit"),
                "author": post.get("author"),
                "link": post.get("link"),
                "date": published[:10] if published else None,
                "published": published,
            }
        )
    threads.sort(key=lambda t: t.get("published") or "", reverse=True)
    for thread in threads:
        thread.pop("published", None)
    return threads


# ── github ──────────────────────────────────────────────────────────────────

def score_github(by_date: dict, latest: str) -> list:
    """Repos score on daily star velocity vs their own baseline, not star count.

    Star count alone just ranks by project age forever. Velocity is the signal.
    """
    dates = sorted(by_date)
    stars = {}   # repo -> {date: stars}
    for date in dates:
        for repo in by_date[date].get("items", []):
            stars.setdefault(repo["repo"], {})[date] = repo.get("stars", 0)

    today = by_date.get(latest, {}).get("items", [])
    peak_stars = max((r.get("stars", 0) for r in today), default=0)

    signals = []
    for repo in today:
        name = repo["repo"]
        series = stars.get(name, {})
        ordered = sorted(series)

        deltas = []
        for previous, current in zip(ordered, ordered[1:]):
            if days_between(current, latest) > BASELINE_DAYS or current == latest:
                continue
            gap = max(days_between(previous, current), 1)
            deltas.append((series[current] - series[previous]) / gap)

        today_delta = None
        before = [d for d in ordered if d < latest]
        if before:
            previous = before[-1]
            gap = max(days_between(previous, latest), 1)
            today_delta = (series[latest] - series[previous]) / gap

        z = zscore(today_delta, deltas) if today_delta is not None else None

        # A repo only becomes a signal when it has a release to point at. Tools with
        # no release mechanism (e.g. Klipper ships from main) stay in data/raw/ for
        # reference but never reach trend-signals.json — there is no artefact to
        # brief an article around.
        release = repo.get("latest_release")
        if not release:
            continue

        fresh_release = False
        if release.get("published_at"):
            published = datetime.fromisoformat(
                release["published_at"].replace("Z", "+00:00")
            )
            age = (datetime.now(timezone.utc) - published).days
            fresh_release = age <= 7

        if z is not None:
            score = spike_to_score(z)
        else:
            score = normalise(repo.get("stars", 0), peak_stars)
        if fresh_release:
            score = round(clamp(score + 10), 1)  # a release this week is news

        metric = (
            f"{repo.get('stars', 0)} stars · "
            f"{repo.get('open_issues_count', 0)} open issues/PRs · {release['tag']}"
        )
        if today_delta is not None:
            metric += f" · {today_delta:+.1f} stars/day"

        # Stable across runs so the Airtable upsert matches. A new release tag mints
        # a new key on purpose — that is a distinct, newly detected signal.
        key = f"github-{slug(name.split('/')[-1])}-{slug(release['tag'])}"

        release_title = release.get("name") or release["tag"]
        signals.append(
            {
                "key": key,
                "topic": f"{name} {release['tag']}: {release_title}",
                "source": "github",
                "category": repo.get("category"),
                "detail": release.get("body_excerpt") or "",
                "score": score,
                "spike": round(z, 2) if z is not None else None,
                "basis": "spike" if z is not None else "raw",
                "engagement": repo.get("stars", 0),
                "metric": metric,
                "link": release.get("url") or repo.get("url"),
                "date": latest,
            }
        )
    return signals


# ── youtube ─────────────────────────────────────────────────────────────────

def score_youtube(by_date: dict, latest: str) -> list:
    """Recent videos scored against their channel's typical view count."""
    baseline = {}
    for date, payload in by_date.items():
        if date == latest or days_between(date, latest) > BASELINE_DAYS:
            continue
        for video in payload.get("items", []):
            if video.get("views"):
                baseline.setdefault(video.get("channel"), []).append(video["views"])

    today = by_date.get(latest, {}).get("items", [])
    now = datetime.now(timezone.utc)

    recent = []
    for video in today:
        published = video.get("published")
        if not published:
            continue
        try:
            age = (now - datetime.fromisoformat(published.replace("Z", "+00:00"))).days
        except ValueError:
            continue
        if age <= YOUTUBE_RECENT_DAYS:
            recent.append((video, age))

    peak = max((v.get("views") or 0 for v, _ in recent), default=0)

    signals = []
    for video, age in recent:
        views = video.get("views") or 0
        z = zscore(views, baseline.get(video.get("channel"), [])) if views else None
        video_id = video.get("id") or slug(video.get("title") or "unknown")
        signals.append(
            {
                "key": f"youtube-{video_id}",
                "topic": video.get("title"),
                "source": "youtube",
                "detail": video.get("channel"),
                "score": spike_to_score(z) if z is not None else normalise(views, peak),
                "spike": round(z, 2) if z is not None else None,
                "basis": "spike" if z is not None else "raw",
                "engagement": views,
                "metric": f"{views:,} views · {video.get('likes') or 0:,} likes · {age}d old",
                "link": video.get("url"),
                "date": latest,
            }
        )
    return signals


# ── manufacturer (recency-scored) ────────────────────────────────────────────

MANUFACTURER_FRESH_DAYS = 7    # full score inside this window
MANUFACTURER_MAX_DAYS = 30     # zero (and dropped) beyond this


def recency_score(age_days: int) -> float:
    """100 for the first week, linear decay to 0 at 30 days.

    Manufacturer posts carry no engagement number to normalise against, so recency
    is the only signal we have. A brand-new announcement scores highest.
    """
    if age_days <= MANUFACTURER_FRESH_DAYS:
        return 100.0
    if age_days >= MANUFACTURER_MAX_DAYS:
        return 0.0
    span = MANUFACTURER_MAX_DAYS - MANUFACTURER_FRESH_DAYS
    return round(100 * (MANUFACTURER_MAX_DAYS - age_days) / span, 1)


def load_manufacturer_keywords() -> dict:
    """{manufacturer: [lowercased keywords]} for feeds configured as {url, keywords}.

    A feed whose entry is a bare URL string has no keyword filter and is absent
    from this map. Read from sources.json at score time (not baked into the raw
    archive) so the keyword list can be changed and re-applied without re-fetching.
    """
    path = ROOT / "inputs" / "sources.json"
    if not path.exists():
        return {}
    try:
        feeds = json.loads(path.read_text(encoding="utf-8")).get("manufacturer_feeds", {})
    except json.JSONDecodeError:
        return {}
    out = {}
    for name, entry in feeds.items():
        if isinstance(entry, dict) and entry.get("keywords"):
            out[name] = [k.lower() for k in entry["keywords"]]
    return out


def score_manufacturer(by_date: dict, latest: str) -> list:
    """Recency-score blog posts. A keyworded feed only emits title-matching posts."""
    keyword_map = load_manufacturer_keywords()
    today = by_date.get(latest, {}).get("items", [])
    now = datetime.now(timezone.utc)

    signals = []
    kw_stats = {}   # manufacturer -> [matched, total]
    for post in today:
        manufacturer = post.get("manufacturer") or "Unknown"
        title = post.get("title") or "(untitled)"

        # Keyword gate — applied before recency so the printed count reflects the
        # keyword filter over every post from that manufacturer, not just recent ones.
        keywords = keyword_map.get(manufacturer)
        if keywords:
            stats = kw_stats.setdefault(manufacturer, [0, 0])
            stats[1] += 1
            if not any(k in title.lower() for k in keywords):
                continue
            stats[0] += 1

        published = post.get("published")
        if not published:
            continue
        try:
            age = (now - datetime.fromisoformat(published)).days
        except ValueError:
            continue
        if age < 0:
            age = 0
        if age >= MANUFACTURER_MAX_DAYS:
            continue  # stale (score would be 0) — nothing to brief around

        signals.append(
            {
                "key": f"manufacturer-{slug(manufacturer)}-{slug(title)[:60]}",
                "topic": title,
                "source": "manufacturer",
                "category": "Hardware",
                "detail": post.get("summary") or "",
                "score": recency_score(age),
                "spike": None,
                "basis": "recency",
                "engagement": 0,
                "metric": f"{manufacturer} · published {published[:10]} · {age}d ago",
                "link": post.get("link"),
                "date": latest,
            }
        )

    for name, (matched, total) in sorted(kw_stats.items()):
        print(f"[score] {name}: {matched} of {total} posts matched keywords")
    return signals


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    raw = load_raw()
    if not raw:
        raise SystemExit(
            f"No raw data in {RAW_DIR}. Run the fetchers first:\n"
            f"  python fetch_reddit.py && python fetch_github.py && python fetch_youtube.py"
        )

    all_dates = sorted({d for source in raw.values() for d in source})
    latest = all_dates[-1]
    history_days = len(all_dates)

    signals = []
    scorers = {
        "github": score_github,
        "youtube": score_youtube,
        "manufacturer": score_manufacturer,
    }
    for source, scorer in scorers.items():
        if source in raw and latest in raw[source]:
            found = scorer(raw[source], latest)
            signals.extend(found)
            print(f"[score] {source}: {len(found)} signals")
        else:
            print(f"[score] {source}: no data for {latest} — skipped")

    signals.sort(key=lambda s: (s["score"], s["engagement"]), reverse=True)
    signals = signals[:TOP_N]
    for index, signal in enumerate(signals, start=1):
        signal["rank"] = index

    # Reddit rides along unscored.
    if "reddit" in raw and latest in raw["reddit"]:
        recent_threads = collect_reddit_threads(raw["reddit"], latest)
        print(f"[score] reddit: {len(recent_threads)} unscored threads (context only)")
    else:
        recent_threads = []
        print(f"[score] reddit: no data for {latest} — skipped")

    # `mode` describes the GitHub/YouTube baseline state only. Manufacturer signals
    # are recency-scored and don't participate in it.
    bases = {s["basis"] for s in signals if s["basis"] in ("spike", "raw")}
    if not bases:
        mode = "raw-engagement"
    elif bases == {"spike"}:
        mode = "baseline-spike"
    elif bases == {"raw"}:
        mode = "raw-engagement"
    else:
        mode = "mixed"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": latest,
        "mode": mode,
        "baseline_days": BASELINE_DAYS,
        "history_days_available": history_days,
        "signal_count": len(signals),
        "signals": signals,
        "recent_threads": recent_threads,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # Same payload as a JS global. Chrome blocks fetch() against file:// URLs, so
    # the dashboard falls back to loading this when opened by double-click.
    OUT_JS.write_text(
        "window.TREND_SIGNALS = "
        + json.dumps(payload, indent=2, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )

    print(f"[score] mode={mode}, {history_days} day(s) of history")
    print(
        f"[score] wrote {len(signals)} ranked signals + "
        f"{len(recent_threads)} reddit threads to {OUT_JSON}"
    )
    if mode != "baseline-spike":
        need = MIN_BASELINE_SAMPLES + 1
        print(
            f"[score] note: ranking on raw engagement where no baseline exists. "
            f"Spike scoring kicks in per source at ~{need} days of history."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
