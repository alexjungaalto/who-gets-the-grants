# Who gets the grants?

> **These numbers may be wrong.** Everything here is assembled automatically from
> public funding databases that were never designed to be joined, and no figure has
> been checked against anyone's CV. Names are reconstructed statistically, so one
> researcher can be split in two and two can be merged into one; money can be filed
> under the wrong person, employer or country; a missing or zero value nearly always
> means *not found* rather than none. Treat any row as a lead to verify.

A static site showing, for each European country, the computer scientists who
secured the most competitive research funding — and, where a university's course
catalogue is machine-readable, how many courses they are listed as teaching.

    site/index.html          the whole site (Leaflet, no basemap tiles)
    site/data/data.json      generated dataset
    site/data/europe.geojson country outlines

## Funding sources

| Source | Scope | What it gives |
|---|---|---|
| ERC datahub + CORDIS | all countries, calls 2007–2022 | panel PE6 "Computer Science and Informatics" grants, PI names, host institution and country |
| FWF Open API (`openapi.fwf.ac.at`) | Austria, 1995–2026 | grants with a non-zero "Computer Sciences" field share, PI name + ORCID + institution |
| research.fi portal API | Finland, dense from 2020 | Research Council of Finland decisions tagged "Computer and information sciences", with each named person's own share |

The ERC column is the only one measured identically in every country. Austria
and Finland look better funded on totals **only because their national agencies
are the two that have been added so far** — the site says so prominently.

## Things that were not obvious

* **research.fi repeats the whole consortium in every sub-project document.**
  Summing `shareOfFundingInEur` naively multiplies a person's money by the number
  of sub-projects (one Finn came out at €6.3M instead of €0.4M). `scripts/`
  de-duplicates on (person, `consortiumProject`).
* **The ERC datahub writes PI names as one unseparated string** in three
  inconsistent conventions — `LEHTINEN Jaakko Tapani`, `Oulasvirta Antti Olavi`,
  `Daniel Cremers`. Without resolution, `Cremers Daniel` and `Daniel Cremers`
  are two people with separate millions. `scripts/names.py` learns a family-name
  and a given-name lexicon from the ~6.2k unambiguously capitalised strings and
  scores every candidate split. Identity merges only when one given name is a
  prefix of the other, so Laura vs Levente Kovács and Marcin vs Michał Pilipczuk
  stay apart, at the cost of leaving Andrei/Andreas Sabelfeld split.
* **FWF classifies projects into fields with percentages**, so amounts are
  weighted by the "Computer Sciences" share rather than counted whole.
* **The FWF API host serves an incomplete TLS chain**, hence the explicit
  unverified context in `fetch_fwf.py`.

## Teaching

Sisu, the Finnish student-information system, exposes a read-only public API
(`/kori/api/...`). Usefully, every host (`sisu.aalto.fi`, `sisu.helsinki.fi`,
`sisu.tuni.fi` …) answers out of **one index covering all of them**, so a single
crawl reaches several universities. Course units carry `responsibilityInfos`
with teacher person-ids that resolve to names.

`fetch_teaching_sisu.py` enumerates units by course-code prefix (the search
accepts a university filter but ignores it) and attributes each to a university
from the `universityOrgIds` on the record. Covered so far: **Aalto University,
University of Helsinki, Tampere University, University of Jyväskylä** — 1 578
course units, 581 teachers, 80 of them matched to someone in the funding tables.

Curriculum-period ids had to be calibrated per university: Tampere and Jyväskylä
put the year in the id (`uta-lvv-2024`, `jy-CP-2024-2025`), while Aalto and
Helsinki use running counters with *different* offsets — `aalto-LV-75` is
2025/26 but `hy-lv-75` is 2024/25. `merge_teaching.py` fits each offset from the
validity dates of courses citing exactly one period. Getting this wrong silently
emptied the whole Aalto column in an earlier cut.

The metric is **distinct catalogue courses on which a person is listed as
responsible teacher or teacher, in curriculum periods overlapping the last five
academic years**. Sisu has no listing endpoint for per-semester realisations, so
semesters taught and contact hours are not obtainable. Email addresses returned
by the person endpoint are discarded, never stored.

Austrian catalogues are not reachable the same way: TU Wien's TISS is a
JavaScript application that renders nothing to a plain GET, and JKU's KUSSS
answers 403 to scripted requests. Covering them needs per-page browser
automation, which has not been done.

Empty cells mean **not retrieved**, never "taught nothing".

## Publishing

The site is published **only** to GitHub Pages at
<https://alexjungaalto.github.io/who-gets-the-grants/>, served from the `docs/`
folder of `main`. `publish.py` rebuilds `docs/` from `site/` on every run, so the
local and published copies cannot drift:

    python3 publish.py --dry-run     # show the steps, change nothing
    python3 publish.py -m "what changed"

There is no other deployment target.

## Rebuild

    python3 scripts/fetch_fwf.py              # ~20k FWF projects
    python3 scripts/fetch_researchfi.py       # RCF computer-science decisions
    python3 scripts/build_erc.py              # needs data/raw/cordis_*/ + erc_datahub_projects.json
    python3 scripts/build_fwf.py
    python3 scripts/build_site_data.py
    python3 scripts/fetch_teaching_sisu.py    # slow (~25 min), resumes if re-run
    python3 scripts/merge_teaching.py
    python3 -m http.server 8777 --directory site
