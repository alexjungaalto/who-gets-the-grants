#!/usr/bin/env python3
"""Dump the full FWF Open API (Meilisearch) projects index to data/raw/fwf_projects.json.

The FWF publishes its Research Radar as a public Meilisearch instance; the
search key is served (unauthenticated) from https://openapi.fwf.ac.at/fwfkey/.
No attribute is filterable server-side, so we pull every document and filter
locally.  TLS: the host serves an incomplete certificate chain, hence verify=off.
"""
import json, ssl, sys, time, urllib.request
from pathlib import Path

BASE = "https://openapi.fwf.ac.at"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "fwf_projects.json"


def get(url, key=None, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "eurogrants/1.0"})
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    with urllib.request.urlopen(req, context=CTX, timeout=90) as r:
        body = r.read().decode("utf-8")
    return body if raw else json.loads(body)


def main():
    key = get(f"{BASE}/fwfkey/", raw=True).strip().strip('"')
    docs, offset = [], 0
    while True:
        page = get(f"{BASE}/indexes/projects/documents?limit=1000&offset={offset}", key)
        got = page["results"] if isinstance(page, dict) else page
        if not got:
            break
        docs.extend(got)
        offset += len(got)
        print(f"  fetched {offset}", file=sys.stderr, flush=True)
        if isinstance(page, dict) and offset >= page.get("total", 0):
            break
        time.sleep(0.2)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(docs, ensure_ascii=False))
    print(f"wrote {len(docs)} FWF projects -> {OUT}")


if __name__ == "__main__":
    main()
