"""Pull each manufacturer's blog feed. No auth needed.

Writes data/raw/manufacturer-<date>.json. Feeds come in two flavours and this
handles both: RSS 2.0 (<item>, pubDate as RFC-822, <description>) and Atom
(<entry>, <published> as ISO-8601, <summary>/<content>). Every post's summary is
stripped of HTML and clipped to ~200 chars for the Detail field downstream.

The feed URLs in inputs/sources.json were each verified to return 200 with real
entries before being added — re-verify with a browser or curl before adding more,
and don't assume a path (Shopify blogs are {url}.atom, WordPress {url}/feed, Ghost
{url}/rss/, and some sites expose none at all).
"""

import html
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from _common import fetch, load_sources, save_raw

SUMMARY_CHARS = 200

ATOM = "http://www.w3.org/2005/Atom"
CONTENT = "http://purl.org/rss/1.0/modules/content/"


def strip_html(text: str) -> str:
    """HTML/entities → a clean single-line excerpt, clipped to SUMMARY_CHARS."""
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > SUMMARY_CHARS:
        text = text[:SUMMARY_CHARS].rstrip() + "…"
    return text


def to_iso(raw: str, atom: bool) -> str | None:
    """Normalise a feed date to ISO-8601, or None if it won't parse."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        if atom:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = parsedate_to_datetime(raw)  # RFC-822
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_rss(root: ET.Element, manufacturer: str) -> list:
    items = []
    for item in root.findall(".//item"):
        summary = item.findtext("description") or ""
        if not summary.strip():
            encoded = item.find(f"{{{CONTENT}}}encoded")
            summary = encoded.text if encoded is not None else ""
        raw_date = item.findtext("pubDate")
        items.append(
            {
                "manufacturer": manufacturer,
                "id": item.findtext("guid") or item.findtext("link"),
                "title": (item.findtext("title") or "").strip(),
                "link": item.findtext("link"),
                "published": to_iso(raw_date, atom=False),
                "published_raw": raw_date,
                "summary": strip_html(summary),
            }
        )
    return items


def _atom_link(entry: ET.Element) -> str | None:
    """Prefer the rel=alternate text/html link; fall back to the first href."""
    fallback = None
    for link in entry.findall(f"{{{ATOM}}}link"):
        href = link.get("href")
        if href and link.get("rel", "alternate") == "alternate":
            return href
        if href and fallback is None:
            fallback = href
    return fallback


def parse_atom(root: ET.Element, manufacturer: str) -> list:
    items = []
    for entry in root.findall(f"{{{ATOM}}}entry"):
        summary = entry.findtext(f"{{{ATOM}}}summary") or ""
        if not summary.strip():
            summary = entry.findtext(f"{{{ATOM}}}content") or ""
        raw_date = entry.findtext(f"{{{ATOM}}}published") or entry.findtext(
            f"{{{ATOM}}}updated"
        )
        items.append(
            {
                "manufacturer": manufacturer,
                "id": entry.findtext(f"{{{ATOM}}}id") or _atom_link(entry),
                "title": (entry.findtext(f"{{{ATOM}}}title") or "").strip(),
                "link": _atom_link(entry),
                "published": to_iso(raw_date, atom=True),
                "published_raw": raw_date,
                "summary": strip_html(summary),
            }
        )
    return items


def fetch_feed(manufacturer: str, url: str) -> list:
    # Parse from raw bytes — feeds mix encodings and occasionally carry stray bytes.
    root = ET.fromstring(fetch(url, accept="application/rss+xml, application/atom+xml"))
    tag = root.tag.lower()
    if tag.endswith("feed"):          # Atom root is {namespace}feed
        return parse_atom(root, manufacturer)
    return parse_rss(root, manufacturer)  # rss / rdf


def feed_url(entry) -> str:
    """A feed entry is either a bare URL string or a {"url", "keywords"} object.

    Keywords are a scoring-time concern (see score_signals.py) — this fetcher only
    needs the URL and always pulls everything, so the raw archive stays complete
    if the keyword list is later changed.
    """
    if isinstance(entry, dict):
        return entry.get("url", "")
    return entry


def main() -> int:
    sources = load_sources()
    feeds = sources.get("manufacturer_feeds", {})
    all_items = []
    failures = []

    for index, (manufacturer, entry) in enumerate(feeds.items()):
        url = feed_url(entry)
        try:
            items = fetch_feed(manufacturer, url)
            all_items.extend(items)
            print(f"[manufacturer] {manufacturer}: {len(items)} posts")
        except Exception as error:
            failures.append(manufacturer)
            print(f"[manufacturer] {manufacturer} ({url}): FAILED — {error}", file=sys.stderr)
        if index < len(feeds) - 1:
            time.sleep(1)

    total_failure = bool(failures) and not all_items
    if total_failure:
        print("[manufacturer] nothing fetched — not writing a raw file", file=sys.stderr)
    else:
        path = save_raw("manufacturer", all_items)
        print(f"[manufacturer] wrote {len(all_items)} posts to {path}")

    if failures:
        print(
            f"[manufacturer] {len(failures)} feed(s) failed: {', '.join(failures)}",
            file=sys.stderr,
        )
    return 1 if total_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
