#!/usr/bin/env python3
"""Pull Research Council of Finland computer-science funding decisions from research.fi.

research.fi exposes its Elasticsearch indices through the public portal API
(no key needed).  Each decision carries a nested `fundingGroupPerson` list with
one `shareOfFundingInEur` per (person, organisation) pair, so we can attribute
money to named researchers.

Note on coverage: research.fi's RCF records only become dense from 2020 on
(63 decisions in 2017 vs 958 in 2022), so Finnish totals are a 2020- window,
not a lifetime one.  This is recorded in the output metadata.
"""
import json, urllib.request
from pathlib import Path

BASE = "https://researchfi-api-production.2.rahtiapp.fi/portalapi"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "researchfi_cs.json"
FUNDER = "Research Council of Finland"
FIELD = "Computer and information sciences"
PAGE = 200


def es(index, body):
    req = urllib.request.Request(
        f"{BASE}/{index}/_search", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "eurogrants/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def fetch(funder_filter):
    q = {"bool": {"filter": [
        {"nested": {"path": "fieldsOfScience",
                    "query": {"term": {"fieldsOfScience.nameEnScience.keyword": FIELD}}}}]}}
    if funder_filter:
        q["bool"]["filter"].append({"term": {"funderNameEn.keyword": funder_filter}})
    out, frm = [], 0
    while True:
        r = es("funding", {"size": PAGE, "from": frm, "query": q,
                           "sort": [{"fundingStartYear": "asc"}], "track_total_hits": True})
        hits = r["hits"]["hits"]
        if not hits:
            break
        out.extend(h["_source"] for h in hits)
        frm += len(hits)
        if frm >= r["hits"]["total"]["value"]:
            break
    return out


def main():
    rcf = fetch(FUNDER)
    allf = fetch(None)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"funder": FUNDER, "field": FIELD,
                               "rcf": rcf, "all_funders": allf}, ensure_ascii=False))
    print(f"RCF CS decisions: {len(rcf)}; all-funder CS decisions: {len(allf)} -> {OUT}")


if __name__ == "__main__":
    main()
