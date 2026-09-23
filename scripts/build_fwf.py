#!/usr/bin/env python3
"""Build the FWF (Austrian Science Fund) computer-science grant table.

Source: the FWF Open API (a public Meilisearch instance behind the Research
Radar), dumped by scripts/fetch_fwf.py.  Unlike the ERC datahub this already
carries a clean principal-investigator name, an ORCID for many records, and the
host institution with its ROR id -- so no name reconstruction is needed.

FWF classifies each project into OECD research fields WITH PERCENTAGES, e.g.
"Computer Sciences (70%); Mathematics (30%)".  We keep any project with a
non-zero "Computer Sciences" share and weight its approved amount by that
share, so a 20%-computer-science biology grant contributes 20% of its money
rather than all of it.  `eur_full` keeps the unweighted amount for reference.
"""
import json, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIELD = "Computer Sciences"


def shares(s):
    """'Computer Sciences (70%); Mathematics (30%)' -> {'Computer Sciences': 0.7, ...}"""
    out = {}
    for part in (s or "").split(";"):
        m = re.match(r"\s*(.+?)\s*\((\d+)%\)\s*$", part)
        if m:
            out[m.group(1)] = int(m.group(2)) / 100.0
    return out


def main():
    docs = json.load(open(ROOT / "data" / "raw" / "fwf_projects.json"))
    rows = []
    for r in docs:
        sh = shares(r.get("_str.researchfields.en"))
        frac = sh.get(FIELD)
        if frac is None:
            # a few records carry the list but not the percentage string
            if FIELD in (r.get("_list.researchfields.en") or []):
                frac = 1.0 / max(len(r["_list.researchfields.en"]), 1)
            else:
                continue
        first = (r.get("_str.principalinvestigator.firstname") or "").strip()
        last = (r.get("_str.principalinvestigator.lastname") or "").strip()
        if not last:
            continue
        amount = float(r.get("_long.approvedamount") or 0)
        date = r.get("_date.approvaldate") or ""
        rows.append({
            "person_key": (r.get("_str.principalinvestigator.orcid") or "").strip()
                          or f"{last.lower()}|{first.lower()}",
            "first": first, "last": last,
            "orcid": r.get("_str.principalinvestigator.orcid") or "",
            "grant_number": r.get("_str.grantdoi") or r.get("id"),
            "title": r.get("_str.projecttitle.en") or r.get("_str.projecttitle.de"),
            "scheme": r.get("_str.program.en") or r.get("_str.program.de"),
            "year": int(date[:4]) if date[:4].isdigit() else None,
            "cs_share": frac,
            "eur": amount * frac,
            "eur_full": amount,
            "host": r.get("_str.principalinvestigator.researchinstitute.name") or "",
            "host_ror": r.get("_str.principalinvestigator.researchinstitute.ror") or "",
            "url": r.get("_str.url") or "",
            "status": r.get("_str.status.en") or "",
        })
    df = pd.DataFrame(rows)
    out = ROOT / "data" / "processed" / "fwf_cs_grants.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} FWF computer-science grants, {df.person_key.nunique()} people, "
          f"{df.eur.sum()/1e6:.0f} M EUR CS-weighted "
          f"({df.eur_full.sum()/1e6:.0f} M unweighted) -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
