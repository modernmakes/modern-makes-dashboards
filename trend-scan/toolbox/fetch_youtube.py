"""Pull the public RSS feed for each channel in sources.json. No API key needed.

Writes data/raw/youtube-<date>.json. The feed carries the ~15 most recent videos
per channel, including view and like counts under the media: namespace.
"""

import sys
import time
import xml.etree.ElementTree as ET

from _common import fetch, load_sources, save_raw

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id="

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def fetch_channel(name: str, channel_id: str) -> list:
    raw = fetch(FEED + channel_id, accept="application/atom+xml")
    root = ET.fromstring(raw)

    items = []
    for entry in root.findall("atom:entry", NS):
        group = entry.find("media:group", NS)
        community = group.find("media:community", NS) if group is not None else None

        views = likes = None
        if community is not None:
            statistics = community.find("media:statistics", NS)
            if statistics is not None:
                views = _int(statistics.get("views"))
            rating = community.find("media:starRating", NS)
            if rating is not None:
                likes = _int(rating.get("count"))

        description = None
        if group is not None:
            node = group.find("media:description", NS)
            if node is not None:
                description = (node.text or "")[:500]

        link = entry.find("atom:link", NS)
        items.append(
            {
                "id": entry.findtext("yt:videoId", namespaces=NS),
                "channel": name,
                "channel_id": channel_id,
                "title": entry.findtext("atom:title", namespaces=NS),
                "published": entry.findtext("atom:published", namespaces=NS),
                "updated": entry.findtext("atom:updated", namespaces=NS),
                "url": link.get("href") if link is not None else None,
                "views": views,
                "likes": likes,
                "description": description,
            }
        )
    return items


def main() -> int:
    sources = load_sources()
    channels = sources.get("youtube_channels", {})
    all_items = []
    failures = []

    for index, (name, channel_id) in enumerate(channels.items()):
        try:
            items = fetch_channel(name, channel_id)
            all_items.extend(items)
            print(f"[youtube] {name}: {len(items)} videos")
        except Exception as error:
            # A wrong channel ID 404s here — the most likely failure by far.
            failures.append((name, error))
            print(
                f"[youtube] {name} ({channel_id}): FAILED — {error}", file=sys.stderr
            )
        if index < len(channels) - 1:
            time.sleep(1)

    path = save_raw("youtube", all_items)
    print(f"[youtube] wrote {len(all_items)} videos to {path}")

    if failures:
        print(
            f"[youtube] {len(failures)} channel(s) failed — verify the channel_id "
            f"in inputs/sources.json against the channel page source",
            file=sys.stderr,
        )
    return 1 if failures and not all_items else 0


if __name__ == "__main__":
    raise SystemExit(main())
