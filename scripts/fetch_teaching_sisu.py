#!/usr/bin/env python3
"""Count catalogue courses per teacher at the Finnish universities served by Sisu.

Sisu is the student-information system most Finnish universities share.  Its
read-only public API sits behind the student portal and, usefully, every host
(sisu.aalto.fi, sisu.helsinki.fi, sisu.tuni.fi ...) answers out of ONE index
covering all of them, so a single crawl reaches several universities:

    /kori/api/course-unit-search?fullTextQuery=...   enumerate course units
    /kori/api/course-units/v1/{id}                   one unit + responsibilityInfos
    /kori/api/persons/v1/{id}                        resolve a personId to a name

The search takes no university filter (the parameter is accepted and ignored),
so units are enumerated by course-code prefix and attributed afterwards with the
`universityOrgIds` each record carries.

What is counted
---------------
A *course unit* (a course in the catalogue), not a course *realisation* (one
semester's delivery): Sisu exposes no listing endpoint for realisations, so
per-semester instances cannot be enumerated.  The metric is therefore "distinct
catalogue courses on which this person is listed as responsible teacher or
teacher, in curriculum periods overlapping the last five academic years".  It is
a lower bound for someone who repeats a course yearly, and says nothing about
contact hours or class size.

Emails come back from the person endpoint; they are deliberately discarded.
Re-running resumes: units already in the output file are not fetched again.
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://sisu.aalto.fi/kori/api"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "teaching_sisu.json"
LEGACY = ROOT / "data" / "raw" / "teaching_aalto.json"

# course-code prefixes per university; the search is prefix-ish full text
PREFIXES = {
    "aalto-university-root-id": ["CS-A", "CS-C", "CS-E", "CS-EJ", "ELEC-E",
                                 "SCI-C", "SCI-E", "MS-E", "MS-C"],
    "hy-university-root-id": ["CSM", "TKT", "DATA1", "BSCS"],
    "tuni-university-root-id": ["COMP.CS", "DATA.ML", "DATA.STAT"],
    "jyu-university-root-id": ["ITKST", "TIES", "TIEA"],
}
UNIVERSITY = {
    "aalto-university-root-id": "Aalto University",
    "hy-university-root-id": "University of Helsinki",
    "tuni-university-root-id": "Tampere University",
    "jyu-university-root-id": "University of Jyväskylä",
}
TEACHER_ROLES = ("responsible-teacher", "teacher", "contact-info")


def get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "eurogrants/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.5 * (attempt + 1))


def search(prefix):
    out, start = [], 0
    while True:
        q = urllib.parse.urlencode({"fullTextQuery": prefix, "limit": 100,
                                    "start": start, "uiLang": "en"})
        d = get(f"course-unit-search?{q}")
        hits = (d or {}).get("searchResults") or []
        if not hits:
            break
        out.extend(hits)
        start += len(hits)
        if start >= (d.get("total") or 0):
            break
        time.sleep(0.1)
    return out


def main():
    units, persons = {}, {}
    for fp in (OUT, LEGACY):                       # resume from earlier runs
        if fp.exists():
            old = json.load(open(fp))
            persons.update(old.get("persons", {}))
            for u in old.get("units", []):
                units.setdefault(u["id"], u)
    print(f"resuming with {len(units)} units, {len(persons)} people", file=sys.stderr)

    wanted = {}
    for org, prefixes in PREFIXES.items():
        for p in prefixes:
            for h in search(p):
                if org in (h.get("universityOrgIds") or []):
                    wanted[h["id"]] = (h.get("code"), org)
            print(f"  {p}: {len(wanted)} candidate units", file=sys.stderr, flush=True)

    todo = [(i, v) for i, v in wanted.items() if i not in units]
    print(f"{len(todo)} new units to fetch", file=sys.stderr, flush=True)
    for n, (uid, (code, org)) in enumerate(todo, 1):
        u = get(f"course-units/v1/{uid}")
        if not u:
            continue
        teachers = []
        for r in u.get("responsibilityInfos") or []:
            role = (r.get("roleUrn") or "").rsplit(":", 1)[-1]
            pid = r.get("personId")
            if pid and role in TEACHER_ROLES:
                teachers.append({"person_id": pid, "role": role})
                if pid not in persons:
                    pr = get(f"persons/v1/{pid}") or {}
                    persons[pid] = {            # email deliberately not kept
                        "first": pr.get("firstName") or "",
                        "last": pr.get("lastName") or "",
                        "title": (pr.get("titles") or [{}])[0].get("en") or "",
                    }
                    time.sleep(0.05)
        units[uid] = {"id": uid, "code": code, "university": org,
                      "name": (u.get("name") or {}).get("en") or (u.get("name") or {}).get("fi"),
                      "curriculum_periods": u.get("curriculumPeriodIds") or [],
                      "validity": u.get("validityPeriod") or {},
                      "teachers": teachers}
        if n % 50 == 0:
            print(f"  {n}/{len(todo)}", file=sys.stderr, flush=True)
        time.sleep(0.05)

    # units carried over from the Aalto-only run have no university field
    for u in units.values():
        u.setdefault("university", "aalto-university-root-id")

    OUT.write_text(json.dumps({"units": list(units.values()), "persons": persons,
                               "universities": UNIVERSITY}, ensure_ascii=False))
    print(f"{len(units)} units, {len(persons)} teachers -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
