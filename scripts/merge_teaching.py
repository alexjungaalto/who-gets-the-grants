#!/usr/bin/env python3
"""Attach course counts from university catalogues to the people in site/data.json.

Currently one adapter: Aalto University via Sisu (data/raw/teaching_aalto.json).

The count is of DISTINCT CATALOGUE COURSES on which the person is listed as
responsible teacher or teacher, restricted to curriculum periods that overlap
the last five academic years.  It is not a count of semesters taught or of
contact hours, and Sisu offers no listing endpoint for per-semester
realisations, so this is the finest granularity available.

Matching to the funding tables is by (family name, first given name) within the
country, the same rule used elsewhere in this project.
"""
import json, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "data" / "data.json"
CURRENT_ACADEMIC_YEAR = 2026        # 2026/27 is running as this is built
WINDOW_START = 2021                 # academic years 2021/22 .. 2025/26
WINDOW_LABEL = "2021/22–2025/26"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z ]", " ", s).lower().split()


def key(last, first):
    lt, ft = norm(last), norm(first)
    return (" ".join(lt), ft[0] if ft else "")


def calibrate(units):
    """Map each curriculum-period id to the academic year it starts.

    Every university numbers its periods its own way.  Tampere and Jyvaskyla
    put the year in the id ('uta-lvv-2024', 'jy-CP-2024-2025'); Aalto and
    Helsinki use running counters ('aalto-LV-75', 'hy-lv-74') whose offset
    differs between them -- Aalto's 75 is 2025/26, Helsinki's 75 is 2024/25.
    The counters are calibrated against the validity start dates of the courses
    that cite exactly one period, taking the median offset so that a few
    mis-dated courses cannot move it.
    """
    out, seq = {}, defaultdict(list)
    for u in units:
        cps = u.get("curriculum_periods") or []
        start = (u.get("validity") or {}).get("startDate")
        for cp in cps:
            m = re.search(r"(19|20)\d\d", cp)
            if m:
                out[cp] = int(m.group(0))
                continue
            n = re.search(r"(\d+)$", cp)
            if n and len(cps) == 1 and start:
                seq[cp.rsplit("-", 1)[0]].append((int(n.group(1)), int(start[:4])))
    offsets = {}
    for fam, pairs_ in seq.items():
        diffs = sorted(y - n for n, y in pairs_)
        offsets[fam] = diffs[len(diffs) // 2]
    for u in units:
        for cp in u.get("curriculum_periods") or []:
            if cp in out:
                continue
            n = re.search(r"(\d+)$", cp)
            fam = cp.rsplit("-", 1)[0]
            if n and fam in offsets:
                out[cp] = int(n.group(1)) + offsets[fam]
    return out


def sisu_counts():
    fp = ROOT / "data" / "raw" / "teaching_sisu.json"
    if not fp.exists():
        return {}, {}
    d = json.load(open(fp))
    period_year = calibrate(d["units"])
    unis = d.get("universities", {})
    counts, detail = defaultdict(set), defaultdict(set)
    for u in d["units"]:
        years = [period_year.get(cp) for cp in u["curriculum_periods"]]
        years = [y for y in years if y]
        # keep a course whose curriculum periods overlap the window at all
        if not years or max(years) < WINDOW_START or min(years) > CURRENT_ACADEMIC_YEAR:
            continue
        for t in u["teachers"]:
            p = d["persons"].get(t["person_id"])
            if not p or not p["last"]:
                continue
            k = key(p["last"], p["first"])
            counts[k].add(u["code"])
            detail[k].add(unis.get(u.get("university"), ""))
    return {k: len(v) for k, v in counts.items()}, {k: sorted(v) for k, v in detail.items()}


def main():
    data = json.load(open(SITE))
    counts, where = sisu_counts()
    if not counts:
        print("no teaching data found -- run fetch_teaching_aalto.py first", file=sys.stderr)
        return

    covered = sorted({u for v in where.values() for u in v if u})
    hit, eligible = 0, 0
    for p in data["people"]:
        if p["country"] != "FI":
            continue
        # only claim a count for someone whose own employer was actually crawled
        if not any(u in (p["host"] or "") for u in covered):
            continue
        eligible += 1
        name = p["name"].rsplit(" ", 1)
        k = key(name[-1], name[0] if len(name) > 1 else "")
        if k in counts:
            p["teaching"] = {"courses": counts[k], "window": WINDOW_LABEL,
                             "source": " / ".join(where[k]) + " course catalogue (Sisu)",
                             "url": "https://sisu.aalto.fi/student/search/courseunit",
                             "unit": "distinct catalogue courses as listed teacher"}
            hit += 1

    data["meta"]["teaching"] = {
        "window": WINDOW_LABEL,
        "covered": covered,
        "metric": "distinct catalogue courses on which the person is listed as "
                  "responsible teacher or teacher",
    }
    SITE.write_text(json.dumps(data, ensure_ascii=False))
    print(f"teaching attached to {hit} of {eligible} people at covered universities "
          f"({', '.join(covered)})", file=sys.stderr)


if __name__ == "__main__":
    main()
