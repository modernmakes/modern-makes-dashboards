"""Pull recent threads from each subreddit's public RSS feed.

Writes data/raw/reddit-<date>.json as an UNSCORED list.

Why RSS and nothing else: Reddit closed self-service API app approval in Nov 2025
and shut off the unauthenticated .json endpoints in May 2026 (403 Blocked). The
per-subreddit RSS feed (https://www.reddit.com/r/<sub>/.rss) still needs no auth,
but it carries only titles, links, and dates — no score, no comment count. There
is nothing here to build an engagement score from, so score_signals.py treats
these as context ("recent community threads"), never as ranked signals. Do not
invent a score for them.
"""

import sys
import time
import xml.etree.ElementTree as ET

from _common import fetch, load_sources, save_raw

LIMIT = 25
FEED = "https://www.reddit.com/r/{sub}/.rss?limit={limit}"

NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_subreddit(subreddit: str) -> list:
    # Parse from raw bytes, not a decoded str: the feed occasionally carries lone
    # surrogates that blow up str-based XML parsing on Windows.
    raw = fetch(FEED.format(sub=subreddit, limit=LIMIT), accept="application/atom+xml")
    root = ET.fromstring(raw)

    items = []
    for entry in root.findall("atom:entry", NS):
        link = entry.find("atom:link", NS)
        author = entry.find("atom:author/atom:name", NS)
        items.append(
            {
                "id": entry.findtext("atom:id", namespaces=NS),
                "subreddit": subreddit,
                "title": entry.findtext("atom:title", namespaces=NS),
                "author": author.text if author is not None else None,
                "published": entry.findtext("atom:published", namespaces=NS),
                "updated": entry.findtext("atom:updated", namespaces=NS),
                "link": link.get("href") if link is not None else None,
            }
        )
    return items


def main() -> int:
    sources = load_sources()
    subreddits = sources.get("subreddits", [])
    all_items = []
    failures = []

    for index, subreddit in enumerate(subreddits):
        try:
            items = fetch_subreddit(subreddit)
            all_items.extend(items)
            print(f"[reddit] r/{subreddit}: {len(items)} threads")
        except Exception as error:  # one dead sub must not kill the batch
            failures.append(subreddit)
            print(f"[reddit] r/{subreddit}: FAILED — {error}", file=sys.stderr)
        if index < len(subreddits) - 1:
            # Reddit's RSS limiter is stingy — 2s between feeds drew 429s on the
            # 3rd/4th sub. 5s keeps a 4-sub run clean while still finishing in ~20s.
            time.sleep(5)

    total_failure = bool(failures) and not all_items
    if total_failure:
        # Never write an empty file for a failed fetch — a downstream reader would
        # take it as "no threads today" rather than "we never got an answer".
        print("[reddit] nothing fetched — not writing a raw file", file=sys.stderr)
        print(
            "[reddit] all RSS requests failed. The feeds need no auth, so this is "
            "usually a network problem or a subreddit that has gone private.",
            file=sys.stderr,
        )
    else:
        path = save_raw("reddit", all_items)
        print(f"[reddit] wrote {len(all_items)} unscored threads to {path}")

    return 1 if total_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
