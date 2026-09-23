#!/usr/bin/env python3
"""Combine ERC / FWF / Research Council of Finland into one site dataset.

Output: site/data.json  ->  {meta, countries[], people[]}

Cross-source identity
---------------------
An Austrian professor can appear in both the ERC table and the FWF table; a
Finn in both the ERC table and the research.fi table.  We merge on
(family name, first given name) with the same prefix rule used inside the ERC
name resolver, restricted to people in the same country, so two same-named
researchers in different countries are never fused.
"""
import json, re, sys, unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from institutions import clean as clean_host

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

COUNTRY = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CH": "Switzerland",
    "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark",
    "EE": "Estonia", "EL": "Greece", "GR": "Greece", "ES": "Spain",
    "FI": "Finland", "FR": "France", "HR": "Croatia", "HU": "Hungary",
    "IE": "Ireland", "IL": "Israel", "IS": "Iceland", "IT": "Italy",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta",
    "NL": "Netherlands", "NO": "Norway", "PL": "Poland", "PT": "Portugal",
    "RO": "Romania", "RS": "Serbia", "SE": "Sweden", "SI": "Slovenia",
    "SK": "Slovakia", "TR": "Türkiye", "UK": "United Kingdom", "GB": "United Kingdom",
}
# ERC associated countries that are not geographically in Europe
ASSOCIATED = {"IL", "TR"}

NATIONAL = {
    "AT": {"name": "FWF", "long": "Austrian Science Fund (FWF)",
           "note": "All FWF grants tagged with a non-zero 'Computer Sciences' "
                   "field share, 1995-2026; amounts weighted by that share.",
           "url": "https://pf.fwf.ac.at/"},
    "FI": {"name": "RCF", "long": "Research Council of Finland",
           "note": "Decisions tagged 'Computer and information sciences' in "
                   "research.fi. Coverage is dense only from 2020 on.",
           "url": "https://research.fi/"},
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z ]", " ", s).lower().split()


def ident(last, first):
    lt, ft = norm(last), norm(first)
    return (" ".join(lt), ft[0] if ft else "")


def link(people):
    """Union people whose given name is a prefix of another's, within a country."""
    groups = defaultdict(set)
    for (country, last, first) in people:
        groups[(country, last)].add(first)
    alias = {}
    for (country, last), firsts in groups.items():
        for a in sorted(firsts, key=len):
            for b in firsts:
                if a != b and len(a) >= 3 and b.startswith(a):
                    alias[(country, last, b)] = (country, last, a)
    return alias


def main():
    erc = pd.read_csv(PROC / "erc_pe6_grants.csv")
    fwf = pd.read_csv(PROC / "fwf_cs_grants.csv")
    fi = json.load(open(ROOT / "data" / "raw" / "researchfi_cs.json"))

    recs = defaultdict(lambda: {"erc_eur": 0.0, "nat_eur": 0.0, "erc": [], "nat": [],
                                "hosts": defaultdict(float), "names": defaultdict(int)})
    raw_ids = []

    def add(country, last, first, host, bucket, grant, eur):
        last_n, first_n = ident(last, first)
        if not last_n:
            return
        key = (country, last_n, first_n)
        raw_ids.append(key)
        r = recs[key]
        r[f"{bucket}_eur"] += eur
        r[bucket].append(grant)
        host = clean_host(host, country)
        if host:
            r["hosts"][host] += eur
        r["names"][f"{first} {last}".strip()] += 1

    for _, g in erc.iterrows():
        if not isinstance(g.country, str):
            continue
        # prefer the full legal name: CORDIS short names are bare acronyms
        # ('LU', 'UOXF') that read badly once title-cased
        host = g.host if isinstance(g.host, str) and g.host.strip() \
            else (g.host_short if isinstance(g.host_short, str) else "")
        add(g.country, g["last"], g["first"], host,
            "erc", {"id": g.grant_number, "acronym": g.acronym, "title": g.title,
                    "scheme": g.scheme, "year": None if pd.isna(g.year) else int(g.year),
                    "eur": round(float(g.eur))}, float(g.eur))

    for _, g in fwf.iterrows():
        add("AT", g["last"], g["first"], g.host,
            "nat", {"id": g.grant_number, "title": g.title, "scheme": g.scheme,
                    "year": None if pd.isna(g.year) else int(g.year),
                    "eur": round(float(g.eur)), "share": float(g.cs_share),
                    "url": g.url if isinstance(g.url, str) else ""}, float(g.eur))

    seen = set()
    for dec in fi["rcf"]:
        for p in dec.get("fundingGroupPerson") or []:
            last = (p.get("fundingGroupPersonLastName") or "").strip()
            first = (p.get("fundingGroupPersonFirstNames") or "").strip()
            sub = p.get("consortiumProject") or p.get("source_id")
            if not last:
                continue
            k = (ident(last, first), sub)
            if k in seen:          # the member list repeats in every sub-project doc
                continue
            seen.add(k)
            org = (p.get("consortiumOrganizationNameEn") or "").strip() or \
                  (dec.get("fundedPersonOrganizationNameEn") or "").strip()
            add("FI", last, first, org,
                "nat", {"id": str(sub), "title": dec.get("projectNameEn") or dec.get("projectNameFi"),
                        "scheme": dec.get("typeOfFundingNameEn"),
                        "year": dec.get("fundingStartYear"),
                        "eur": round(p.get("shareOfFundingInEur") or 0),
                        "role": p.get("roleInFundingGroup")},
                float(p.get("shareOfFundingInEur") or 0))

    alias = link(raw_ids)
    merged = defaultdict(lambda: {"erc_eur": 0.0, "nat_eur": 0.0, "erc": [], "nat": [],
                                  "hosts": defaultdict(float), "names": defaultdict(int)})
    for key, r in recs.items():
        m = merged[alias.get(key, key)]
        for f in ("erc_eur", "nat_eur"):
            m[f] += r[f]
        for f in ("erc", "nat"):
            m[f] += r[f]
        for h, v in r["hosts"].items():
            m["hosts"][h] += v
        for n, v in r["names"].items():
            m["names"][n] += v

    people = []
    for (country, last_n, first_n), r in merged.items():
        # most frequently written form; on a tie take the shortest, so that
        # 'Antti Oulasvirta' beats the datahub's 'Antti Olavi Oulasvirta'
        name = min(r["names"].items(), key=lambda x: (-x[1], len(x[0])))[0]
        host = max(r["hosts"].items(), key=lambda x: x[1])[0] if r["hosts"] else ""
        host = clean_host(host, country)
        people.append({
            "id": f"{country}:{last_n}:{first_n}".replace(" ", "_"),
            "name": name, "country": country, "host": host,
            "erc_eur": round(r["erc_eur"]), "nat_eur": round(r["nat_eur"]),
            "total_eur": round(r["erc_eur"] + r["nat_eur"]),
            "erc_grants": sorted(r["erc"], key=lambda g: g.get("year") or 0),
            "nat_grants": sorted(r["nat"], key=lambda g: g.get("year") or 0),
            "teaching": None,
        })
    people.sort(key=lambda p: -p["total_eur"])

    countries = []
    for code in sorted({p["country"] for p in people}):
        ps = [p for p in people if p["country"] == code]
        countries.append({
            "code": code, "name": COUNTRY.get(code, code),
            "associated": code in ASSOCIATED,
            "n_people": len(ps),
            "erc_eur": sum(p["erc_eur"] for p in ps),
            "nat_eur": sum(p["nat_eur"] for p in ps),
            "erc_grants": sum(len(p["erc_grants"]) for p in ps),
            "national": NATIONAL.get(code),
        })
    countries.sort(key=lambda c: -(c["erc_eur"] + c["nat_eur"]))

    out = {
        "meta": {
            "generated": date.today().isoformat(),
            "erc_years": "2007-2022 calls (panel PE6, Computer Science and Informatics)",
            "sources": [
                {"name": "ERC datahub + CORDIS", "what": "ERC PE6 grants, PI names, host country",
                 "url": "https://cordis.europa.eu/datalab/"},
                {"name": "FWF Open API", "what": "Austrian Science Fund computer-science grants",
                 "url": "https://pf.fwf.ac.at/en/discover/open-api"},
                {"name": "research.fi portal API", "what": "Research Council of Finland CS decisions",
                 "url": "https://research.fi/"},
            ],
        },
        "countries": countries,
        "people": people,
    }
    (ROOT / "site" / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "site" / "data" / "data.json").write_text(json.dumps(out, ensure_ascii=False))
    print(f"{len(people)} people in {len(countries)} countries -> site/data/data.json", file=sys.stderr)
    for c in countries[:12]:
        print(f"  {c['code']} {c['name']:<16} people={c['n_people']:4d} "
              f"ERC={c['erc_eur']/1e6:7.1f}M nat={c['nat_eur']/1e6:7.1f}M", file=sys.stderr)


if __name__ == "__main__":
    main()
