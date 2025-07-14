#!/usr/bin/env python3
import sys
import json
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
FLOORPLAN_URL = "https://maccommons.com/floorplans/jr-1-bedroom-b/"
UNIT_URL_FMT = "https://maccommons.com/floorplans/unit-{slug}/"
OUTPUT_DIR = "snapshots"  # make sure this exists
TIMEOUT = 10  # seconds
# -------------------------------------------------------------------

def make_session():
    """Create a requests.Session that will retry on common transient errors."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = make_session()

def fetch_url(url: str) -> str | None:
    """GET a URL with timeout & retry; return text or None on failure."""
    try:
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Warning: could not fetch {url}: {e}", file=sys.stderr)
        return None

def get_floorplan_units() -> list[str]:
    """Scrape the main floorplan page and return all unit slugs."""
    html = fetch_url(FLOORPLAN_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", {"id": "jd-fp-data-script-resource"})
    if not script or not script.string:
        print("⚠️  Could not find floorplan JSON script on the page", file=sys.stderr)
        return []
    data = json.loads(script.string)
    return [u["slug"] for u in data.get("units", []) if u.get("slug")]

def get_unit_data(slug: str) -> dict | None:
    """Fetch the detail page for a single unit slug and return its JSON."""
    url = UNIT_URL_FMT.format(slug=slug)
    html = fetch_url(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="jd-fp-data-script-resource")
    if not script or not script.string:
        print(f"⚠️  Could not find unit JSON script for slug={slug}", file=sys.stderr)
        return None
    return json.loads(script.string)

def main():
    # ISO-8601 UTC timestamp for this run
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    slugs = get_floorplan_units()
    print(f"🔍 Found {len(slugs)} unit slugs, fetching details…")

    results: list[dict] = []
    for slug in slugs:
        unit = get_unit_data(slug)
        if unit:
            unit["scraped_at"] = now
            results.append(unit)

    if not results:
        print("❌ No unit data retrieved, aborting save.", file=sys.stderr)
        sys.exit(1)

    # Re-key by apartment_number for easier lookups and stability
    units_by_number = {
        u["apartment_number"]: u
        for u in results
        if u.get("apartment_number")
    }

    snapshot = {
        "timestamp": now,
        "units": units_by_number
    }

    out_path = f"{OUTPUT_DIR}/snapshot_{now}.json"
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"✅ Saved {len(units_by_number)} units to {out_path}")

if __name__ == "__main__":
    main()


