"""Pull stars, open issues, and latest release for each configured GitHub repo.

Repos are grouped in inputs/sources.json under three keys, each mapping to an
editorial category:

  printer_design_repos -> Printer Design
  firmware_repos       -> Firmware
  slicer_repos         -> Slicer

Every repo is tagged with its category here so downstream steps don't have to
re-derive it. Writes data/raw/github-<date>.json. Two unauthenticated calls per
repo; the default 10 repos cost 20 of the 60/hour anonymous rate limit.
"""

import sys
import time
import urllib.error

from _common import fetch_json, load_sources, save_raw

API = "https://api.github.com/repos"
BODY_EXCERPT_CHARS = 200

# sources.json key -> category label
REPO_LISTS = {
    "printer_design_repos": "Printer Design",
    "firmware_repos": "Firmware",
    "slicer_repos": "Slicer",
    "hardware_repos": "Hardware",
}


def fetch_latest_release(repo: str):
    """Latest published release, or None. Repos with no releases return 404."""
    try:
        release = fetch_json(f"{API}/{repo}/releases/latest")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    body = (release.get("body") or "").strip()
    excerpt = body[:BODY_EXCERPT_CHARS].strip()
    if len(body) > BODY_EXCERPT_CHARS:
        excerpt += "…"
    return {
        "tag": release.get("tag_name"),
        "name": release.get("name"),
        "body_excerpt": excerpt,
        "published_at": release.get("published_at"),
        "url": release.get("html_url"),
    }


def fetch_repo(repo: str, category: str) -> dict:
    data = fetch_json(f"{API}/{repo}")
    return {
        "id": repo,
        "repo": repo,
        "category": category,
        "name": data.get("name"),
        "description": data.get("description"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "watchers": data.get("subscribers_count", 0),
        # GitHub folds open PRs into open_issues_count — it is issues + PRs,
        # not issues alone. Tracked as a trend line, not an absolute.
        "open_issues_count": data.get("open_issues_count", 0),
        "pushed_at": data.get("pushed_at"),
        "url": data.get("html_url"),
        "latest_release": fetch_latest_release(repo),
    }


def collect_repos(sources: dict) -> list:
    """[(repo, category)] flattened across the three configured lists."""
    pairs = []
    for key, category in REPO_LISTS.items():
        for repo in sources.get(key, []):
            pairs.append((repo, category))
    return pairs


def main() -> int:
    sources = load_sources()
    pairs = collect_repos(sources)
    all_items = []
    failures = []

    for index, (repo, category) in enumerate(pairs):
        try:
            item = fetch_repo(repo, category)
            all_items.append(item)
            release = item["latest_release"]
            tag = release["tag"] if release else "no releases"
            print(f"[github] [{category}] {repo}: {item['stars']} stars, {tag}")
        except urllib.error.HTTPError as error:
            failures.append((repo, error))
            hint = " (rate limited — wait an hour)" if error.code == 403 else ""
            print(f"[github] {repo}: FAILED — {error}{hint}", file=sys.stderr)
        except Exception as error:
            failures.append((repo, error))
            print(f"[github] {repo}: FAILED — {error}", file=sys.stderr)
        if index < len(pairs) - 1:
            time.sleep(1)

    path = save_raw("github", all_items)
    print(f"[github] wrote {len(all_items)} repos to {path}")

    if failures:
        print(f"[github] {len(failures)} repo(s) failed", file=sys.stderr)
    return 1 if failures and not all_items else 0


if __name__ == "__main__":
    raise SystemExit(main())
