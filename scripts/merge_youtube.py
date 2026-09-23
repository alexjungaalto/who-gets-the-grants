#!/usr/bin/env python3
"""Attach the YouTube lecture-series findings to site/data/data.json.

This is deliberately kept apart from the course counts.  A catalogue count says
how much someone teaches; a YouTube count says how much of their teaching was
filmed and left public, which is a different thing and mostly a property of the
university and the year rather than the person.  Both are shown, neither is
added to the other.

Three states are distinguished, because collapsing them would mislead:
  searched and a series found -> the number of episodes
  searched and nothing found  -> an explicit zero
  not searched at all         -> null (only the top 15 per country were searched)
"""
import json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from names import build_lexicons
SITE = ROOT / "site" / "data" / "data.json"
RAW = ROOT / "data" / "raw" / "youtube_lectures.json"


def fold(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z ]", " ", s.lower())


# markers of a one-off event rather than a taught course. A hand audit of the
# first 35 detected series found ~8 wrong, and most were of this shape: STOC
# workshop sessions, a memorial "Annual Lecture", an Italian "lectio magistralis",
# a "conferenza". They survive series detection because an event is often
# uploaded in numbered parts, exactly like a course.
EVENT_MARKERS = re.compile(
    r"\b(workshop|conferenza|conference|lectio magistralis|annual lecture|"
    r"memorial|keynote|seminar|colloqui|symposium|panel|stoc|focs|soda|neurips|"
    r"icml|iclr|summit|webinar|five-minute talks)\b", re.I)


# Hand-audited exclusions. The remaining false positives have no structural
# tell that a regex can catch without also throwing away good rows -- 'Anup Rao
# - Three monotone circuit lower bounds' on Bruno Loff's channel looks exactly
# like 'Virtual Memory: 10 ...' on David Black-Schaffer's. Two are plain name
# collisions: the 'Stefan Roth' with a Windows 10 tutorial is not the TU
# Darmstadt vision professor. A short explicit list is more honest and more
# maintainable than an ever more contorted heuristic.
EXCLUDE = {
    ("Stefan Roth", "Stefan Roth"),                 # a different Stefan Roth (IT consultant)
    ("Andrew Stuart Tanenbaum", "LearnEveryone"),   # third party teaching from his textbook
    ("Andrew Stuart Tanenbaum", "Bogdan Sass"),     # a visiting talk cut into parts
    ("Andris Ambainis", "Iqst Ucalgary"),           # research seminar, not teaching
    ("Bruno Loff", "Bruno Loff"),                   # seminar series he hosts for others
}


def is_event(title):
    return bool(EVENT_MARKERS.search(title or ""))


def someone_elses_talk(title, person, given):
    """True when the series is plainly a recording of a DIFFERENT person.

    A researcher's own channel often hosts a seminar series of invited talks --
    Bruno Loff's channel carries 'Mary Wootters - Random ensembles ...' -- and
    attributing those to the channel owner would be simply wrong.  The tell is
    a personal given name in the title that is not the owner's, with the
    owner's own family name absent.  Given names are recognised with the
    lexicon already learned from the ~14k ERC principal-investigator strings,
    which is why 'Programming Parallel Computers' survives and 'Mary Wootters'
    does not.
    """
    words = fold(title).split()
    own = set(fold(person).split())
    if own & set(words):                       # the person is named: keep
        return False
    for i, w in enumerate(words[:-1]):
        if w in own:
            continue
        if given.get(w, 0) >= 2 and words[i + 1] not in own and len(words[i + 1]) > 2:
            return True
    return False


def main():
    if not RAW.exists():
        sys.exit("run fetch_youtube_lectures.py first")
    found = json.load(open(RAW))
    data = json.load(open(SITE))
    dh = json.load(open(ROOT / "data" / "raw" / "erc_datahub_projects.json"))
    _, given = build_lexicons(x for r in dh for x in (r["pis"] or []))

    hits, dropped = 0, []
    for p in data["people"]:
        rec = found.get(p["id"])
        if not rec:
            continue
        series = []
        for s in rec["series"]:
            if someone_elses_talk(s["title"], rec["name"], given):
                dropped.append((rec["name"], "other person", s["title"]))
            elif is_event(s["title"]):
                dropped.append((rec["name"], "one-off event", s["title"]))
            elif (rec["name"], s["channel"]) in EXCLUDE:
                dropped.append((rec["name"], "audited out", s["title"]))
            else:
                series.append(s)
        p["youtube"] = {
            "searched": True,
            "series": len(series),
            "episodes": sum(s["episodes"] for s in series),
            "minutes": sum(s["minutes"] for s in series),
            "items": [{"title": s["title"], "channel": s["channel"],
                       "episodes": s["episodes"], "minutes": s["minutes"],
                       "url": f"https://www.youtube.com/watch?v={s['example_id']}"}
                      for s in series[:4]],
        }
        if series:
            hits += 1

    data["meta"]["youtube"] = {
        "scope": "the 15 best-funded researchers in each country",
        "metric": "numbered lecture series on one channel (at least 3 episodes "
                  "with 3 different episode numbers), attributed to the person by "
                  "channel or title",
        "caveat": "this measures teaching that was filmed and left public, not "
                  "teaching load; one-off keynotes, panels and podcast interviews "
                  "are deliberately excluded",
        "searched": len(found),
        "with_series": hits,
        "precision": "every detected series was checked by hand: of 35 found, "
                     "9 were discarded as one-off events, as talks by other people "
                     "hosted on the researcher's own channel, or as a different "
                     "person with the same name. Of what remains, roughly a third "
                     "are summer-school or public lecture-chair courses rather "
                     "than degree teaching. Each series links to the video.",
    }
    SITE.write_text(json.dumps(data, ensure_ascii=False))
    print(f"{hits} of {len(found)} searched researchers have a lecture series; "
          f"{len(dropped)} series dropped as another person's talk", file=sys.stderr)
    for name, why, title in dropped:
        print(f"    dropped ({why})  {name}: {title[:60]}", file=sys.stderr)


if __name__ == "__main__":
    main()
