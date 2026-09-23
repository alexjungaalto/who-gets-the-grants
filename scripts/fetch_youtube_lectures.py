#!/usr/bin/env python3
"""Find recorded LECTURE SERIES on YouTube for the researchers in the dataset.

Why series detection rather than a keyword search
-------------------------------------------------
Searching '<name> lecture' mostly returns keynotes, panels and podcast
interviews -- for Sepp Hochreiter, all eight top hits are invited talks and not
one is a course.  The word "lecture" in a title is therefore nearly useless as
a signal.  What does separate teaching from talking is that a course comes in a
NUMBERED SERIES from one channel: 'Distributed Algorithms 2020: lecture 1a',
'... 2a', '... 5a'.  A keynote is a singleton.

So: search, keep only videos plausibly by this person (their family name is in
the channel name or the title), group by (channel, title stem before the first
number), and keep groups with at least MIN_EPISODES videos carrying at least
MIN_DISTINCT distinct numbers.

This measures *recorded teaching that is public*, which is not teaching load.
A professor who teaches four courses and films none scores zero.  It is
reported on the site as its own column, never merged into the course counts.

No API key is needed; yt-dlp's `ytsearch` is used in flat mode.
"""
import json, re, subprocess, sys, time, unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "youtube_lectures.json"
QUERIES = ["{name} lecture", "{name} course", "{name} Vorlesung"]
N_RESULTS = 30
MIN_EPISODES = 3          # a series needs at least this many videos
MIN_DISTINCT = 3          # ... carrying at least this many different numbers
MIN_MINUTES = 4           # shorter clips are trailers, not lectures


def fold(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", " ", s.lower())


def search(query, n=N_RESULTS):
    cmd = ["yt-dlp", f"ytsearch{n}:{query}", "--flat-playlist", "--dump-json",
           "--no-warnings", "--socket-timeout", "30"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    except subprocess.TimeoutExpired:
        return []
    rows = []
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append({"id": d.get("id"), "title": d.get("title") or "",
                     "channel": d.get("channel") or d.get("uploader") or "",
                     "channel_id": d.get("channel_id") or "",
                     "duration": d.get("duration") or 0,
                     "views": d.get("view_count") or 0})
    return rows


def stem(title, k=2):
    """The first k non-numeric words -- what the episodes of one series share.

    Cutting the title at its first digit fails on 'BDA 2019 Lecture 9.2 ...',
    where the year comes first and leaves a 3-character stub; taking the
    leading words instead keys 'BDA ... Lecture' and 'Distributed Algorithms
    ... lecture' alike.
    """
    words = [w for w in fold(title).split() if len(w) > 1]
    return " ".join(words[:k])


def numbers(title):
    return set(re.findall(r"\d+", title))


def series_for(person_name, rows):
    """Group a person's hits into plausible course series."""
    last = fold(person_name).split()[-1]
    mine = [r for r in rows
            if r["duration"] >= MIN_MINUTES * 60
            and (last in fold(r["channel"]) or last in fold(r["title"]))]
    groups = defaultdict(list)
    for r in mine:
        s = stem(r["title"])
        if len(s) >= 5 and numbers(r["title"]):
            groups[(r["channel"], s)].append(r)
    out = []
    for (channel, s), vids in groups.items():
        nums = set()
        for v in vids:
            nums |= numbers(v["title"])
        if len(vids) >= MIN_EPISODES and len(nums) >= MIN_DISTINCT:
            vids.sort(key=lambda v: v["title"])
            out.append({"channel": channel, "title": vids[0]["title"],
                        "episodes": len(vids),
                        "minutes": round(sum(v["duration"] for v in vids) / 60),
                        "example_id": vids[0]["id"]})
    out.sort(key=lambda g: -g["episodes"])
    return out, len(mine)


def main():
    names = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else None
    if names is None:
        sys.exit("usage: fetch_youtube_lectures.py people.json")
    done = json.load(open(OUT)) if OUT.exists() else {}
    for i, p in enumerate(names, 1):
        if p["id"] in done:
            continue
        rows, seen = [], set()
        for q in QUERIES:
            for r in search(q.format(name=p["name"])):
                if r["id"] and r["id"] not in seen:
                    seen.add(r["id"])
                    rows.append(r)
            time.sleep(0.3)
        ser, n_mine = series_for(p["name"], rows)
        done[p["id"]] = {"name": p["name"], "series": ser,
                         "candidate_videos": n_mine, "searched": len(rows)}
        if i % 10 == 0 or ser:
            print(f"  [{i}/{len(names)}] {p['name']}: {len(ser)} series "
                  f"({n_mine} candidate videos)", file=sys.stderr, flush=True)
            OUT.write_text(json.dumps(done, ensure_ascii=False))
    OUT.write_text(json.dumps(done, ensure_ascii=False))
    withser = sum(1 for v in done.values() if v["series"])
    print(f"{len(done)} people searched, {withser} with a lecture series -> {OUT}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
