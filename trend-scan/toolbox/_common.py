"""Shared helpers for the trend-scan fetchers.

Every fetcher writes one file per run to data/raw/<source>-<date>.json using the
same envelope so score_signals.py can read them back without special-casing.
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "modern-makes-research/1.0"

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "inputs"
RAW_DIR = ROOT / "data" / "raw"


def today() -> str:
    """UTC date stamp. Raw filenames key off this, so it must not be local time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_sources() -> dict:
    path = INPUTS / "sources.json"
    if not path.exists():
        raise SystemExit(f"Missing {path} — create it before running the fetchers.")
    return json.loads(path.read_text(encoding="utf-8"))


def fetch(url: str, accept: str = "application/json", retries: int = 3):
    """GET a URL with the project User-Agent. Returns raw bytes.

    Backs off on 429/5xx: these APIs are all unauthenticated and rate limits are
    the normal failure mode, not the exceptional one.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise
        except urllib.error.URLError as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise
    raise last_error


def fetch_json(url: str, retries: int = 3):
    return json.loads(fetch(url, retries=retries).decode("utf-8"))


def save_raw(source: str, items: list) -> Path:
    """Write data/raw/<source>-<date>.json, overwriting the same day's earlier run."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{source}-{today()}.json"
    payload = {
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "date": today(),
        "items": items,
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path
