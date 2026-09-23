#!/usr/bin/env python3
"""Build the ERC computer-science (panel PE6) grant table, one row per PI-grant.

Two sources are joined on the EC grant agreement number:

  * the ERC datahub export (data/raw/erc_datahub_projects.json) -- carries the
    evaluation panel and the principal investigator names, neither of which
    CORDIS publishes;
  * the CORDIS project/organization CSVs -- carry the host institution and its
    country, which the datahub export leaves empty.

Panel PE6 is "Computer Science and Informatics".  The datahub export ends with
the 2022 calls, so ERC figures here cover calls 2007-2022.

Synergy grants have several PIs; their budget is split evenly across them, so
that summing `eur` over people reproduces the ERC's total outlay exactly once.
"""
import json, re, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from names import build_lexicons, resolve

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
PANEL = "PE6"


def main():
    dh_raw = json.load(open(RAW / "erc_datahub_projects.json"))
    # lexicons learn from the WHOLE datahub (14k names), not just PE6
    fam, giv = build_lexicons(p for r in dh_raw for p in (r["pis"] or []))
    people = resolve((p for r in dh_raw if r["topic"] == PANEL
                      for p in (r["pis"] or [])), fam, giv)

    dh = pd.DataFrame(dh_raw)
    pe6 = dh[dh.topic == PANEL].copy()
    pe6["number"] = pe6.number.astype(str)
    pe6["budget"] = pd.to_numeric(pe6.budget, errors="coerce").fillna(0)
    pe6["year"] = pe6.call_name.str.extract(r"(20\d\d)").astype("Int64")

    orgs = [pd.read_csv(fp, sep=";", low_memory=False,
                        usecols=["projectID", "name", "shortName", "country",
                                 "role", "organizationURL"])
            for fp in sorted(RAW.glob("cordis_*/organization.csv"))]
    org = pd.concat(orgs)
    org["projectID"] = org.projectID.astype(str)
    host = (org[org.role == "coordinator"].drop_duplicates("projectID")
            .set_index("projectID")[["name", "shortName", "country", "organizationURL"]])

    pe6 = pe6.join(host, on="number")
    print(f"PE6 grants: {len(pe6)}; without host/country: {pe6.country.isna().sum()}",
          file=sys.stderr)

    rows = []
    for _, r in pe6.iterrows():
        pis = r.pis if isinstance(r.pis, list) else []
        for p in pis:
            who = people[p]
            rows.append({
                "person_key": "|".join(who["key"]),
                "first": who["first"], "last": who["last"], "pi_raw": p,
                "grant_number": r.number, "acronym": r.acronym, "title": r.title,
                "scheme": re.sub(r"^ERC[- ]", "", str(r.phase)).strip(),
                "call": r.call_name, "year": (int(r.year) if pd.notna(r.year) else None),
                "eur": float(r.budget) / max(len(pis), 1),
                "grant_eur_total": float(r.budget),
                "host": r["name"], "host_short": r.shortName,
                "country": r.country, "host_url": r.organizationURL,
            })
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "erc_pe6_grants.csv", index=False)
    print(f"wrote {len(df)} PI-grant rows, {df.person_key.nunique()} people "
          f"-> {OUT/'erc_pe6_grants.csv'}", file=sys.stderr)


if __name__ == "__main__":
    main()
