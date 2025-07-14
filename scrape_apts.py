#!/usr/bin/env python3
import requests, json, os
from datetime import datetime
from bs4 import BeautifulSoup

BASE_URL    = "https://maccommons.com"
FLOORPLAN   = "jr-1-bedroom-b"
OUTPUT_DIR  = "snapshots"

def get_floorplan_units():
    url  = f"{BASE_URL}/floorplans/{FLOORPLAN}/"
    resp = requests.get(url); resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    script = soup.find("script", id="jd-fp-data-script-resource")
    data   = json.loads(script.string)
    return [u["slug"] for u in data.get("units", [])]

def get_unit_detail(slug):
    url  = f"{BASE_URL}/floorplans/unit-{slug}/"
    resp = requests.get(url); resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    script = soup.find("script", id="jd-fp-data-script-resource")
    return json.loads(script.string)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for slug in get_floorplan_units():
        detail = get_unit_detail(slug)
        fn = f"{OUTPUT_DIR}/{FLOORPLAN}__{slug}__{now}.json"
        with open(fn, "w") as f:
            json.dump(detail, f, indent=2)
        print("✔ saved", fn)

if __name__=="__main__":
    main()
