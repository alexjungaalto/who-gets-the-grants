#!/usr/bin/env python3
"""Publish the site to GitHub Pages at alexjungaalto.github.io/who-gets-the-grants.

Same shape as the FamilyPolicyEurope deployment: the repository holds the whole
project, and GitHub Pages serves the `docs/` folder of the default branch.
`site/` is the working copy that `python3 -m http.server --directory site`
serves locally; `docs/` is the published copy, rebuilt from it on every run so
the two can never drift.

The script is idempotent -- it creates the repository and turns Pages on only
if they are not there already -- so re-running it is how you deploy an update.

    python3 publish.py --dry-run     # show what would happen, touch nothing
    python3 publish.py               # build docs/, commit, push, enable Pages
    python3 publish.py -m "add YouTube column"

Requirements: `gh` authenticated as the repo owner (`gh auth status`) and git
configured.  data/ is ~570 MB of raw downloads and is excluded by .gitignore;
only the 1.7 MB site and the scripts that build it are published.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OWNER = "alexjungaalto"
REPO = "who-gets-the-grants"
BRANCH = "main"
PAGES_DIR = "docs"
URL = f"https://{OWNER}.github.io/{REPO}/"

# NOTE the leading slash. A bare 'data/' matches a directory of that name at ANY
# depth, which would also swallow site/data/ and docs/data/ -- i.e. publish the
# page without the dataset it reads. Anchor it to the project root.
GITIGNORE = """\
# raw downloads and intermediates: ~570 MB, all reproducible via scripts/
/data/
__pycache__/
*.pyc
.DS_Store
"""


class Fail(SystemExit):
    pass


def run(cmd, *, cwd=ROOT, check=True, capture=True, dry=False):
    if dry:
        print(f"    would run: {' '.join(cmd)}")
        return ""
    p = subprocess.run(cmd, cwd=cwd, text=True,
                       capture_output=capture)
    if check and p.returncode:
        raise Fail(f"{' '.join(cmd)} failed:\n{(p.stderr or p.stdout).strip()}")
    return (p.stdout or "").strip()


def step(msg):
    print(f"==> {msg}")


# --------------------------------------------------------------------------- #
# preflight
# --------------------------------------------------------------------------- #
def preflight():
    step("checking prerequisites")
    if not shutil.which("gh"):
        raise Fail("gh is not installed (brew install gh)")
    who = run(["gh", "api", "user", "--jq", ".login"], check=False)
    if not who:
        raise Fail("gh is not authenticated -- run: gh auth login")
    if who != OWNER:
        print(f"    note: gh is authenticated as {who}, publishing under {OWNER}")
    print(f"    gh ok (account: {who})")

    src = ROOT / "site"
    for f in ("index.html", "data/data.json", "data/europe.geojson"):
        if not (src / f).exists():
            raise Fail(f"missing {src/f} -- run the build scripts first "
                       f"(see README.md)")
    data = json.loads((src / "data" / "data.json").read_text())
    print(f"    site ok ({len(data['people'])} people, "
          f"{len(data['countries'])} countries)")
    return data


# --------------------------------------------------------------------------- #
# build the published copy
# --------------------------------------------------------------------------- #
def build_docs(dry=False):
    """Mirror site/ into docs/ and stamp a cache-busting data version."""
    step(f"building {PAGES_DIR}/ from site/")
    src, dst = ROOT / "site", ROOT / PAGES_DIR
    if dry:
        print(f"    would mirror {src} -> {dst}")
        return "dryrun"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    # GitHub Pages runs Jekyll by default, which skips files beginning with an
    # underscore; .nojekyll turns that off and serves the tree verbatim.
    (dst / ".nojekyll").write_text("")

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    index = dst / "index.html"
    html, n = re.subn(r"const DATA_V='[^']*'", f"const DATA_V='{stamp}'",
                      index.read_text())
    if not n:
        raise Fail("could not find the DATA_V cache-buster in index.html")
    index.write_text(html)

    size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
    print(f"    {PAGES_DIR}/ built, {size/1e6:.1f} MB, data version {stamp}")
    return stamp


# --------------------------------------------------------------------------- #
# repository
# --------------------------------------------------------------------------- #
def ensure_repo(dry=False):
    step(f"ensuring {OWNER}/{REPO} exists")
    exists = run(["gh", "repo", "view", f"{OWNER}/{REPO}", "--json", "name"],
                 check=False) != ""
    if exists:
        print("    repository already exists")
    else:
        print("    creating public repository")
        run(["gh", "repo", "create", f"{OWNER}/{REPO}", "--public",
             "--description",
             "Who gets the grants? Computer-science research funding in Europe"],
            dry=dry)

    if not (ROOT / ".git").exists():
        run(["git", "init", "-b", BRANCH], dry=dry)
    remotes = run(["git", "remote"], check=False)
    url = f"https://github.com/{OWNER}/{REPO}.git"
    if "origin" in remotes.split():
        run(["git", "remote", "set-url", "origin", url], dry=dry)
    else:
        run(["git", "remote", "add", "origin", url], dry=dry)
    print(f"    origin -> {url}")


def commit_and_push(message, dry=False):
    step("committing and pushing")
    gi = ROOT / ".gitignore"
    if not dry and (not gi.exists() or gi.read_text() != GITIGNORE):
        gi.write_text(GITIGNORE)
        print("    wrote .gitignore (excludes data/)")

    run(["git", "add", "-A"], dry=dry)
    status = run(["git", "status", "--porcelain"], check=False)
    if not status and not dry:
        print("    nothing changed since the last publish")
        return False
    run(["git", "commit", "-m", message], check=False, dry=dry)
    run(["git", "branch", "-M", BRANCH], check=False, dry=dry)
    run(["git", "push", "-u", "origin", BRANCH], dry=dry)
    print(f"    pushed to {BRANCH}")
    return True


def ensure_pages(dry=False):
    step("ensuring GitHub Pages serves docs/")
    if dry:
        print(f"    would enable Pages on {BRANCH} /{PAGES_DIR}")
        return
    current = run(["gh", "api", f"repos/{OWNER}/{REPO}/pages",
                   "--jq", ".source.branch + \" \" + .source.path"], check=False)
    want = f"{BRANCH} /{PAGES_DIR}"
    if current == want:
        print(f"    already serving {want}")
        return
    verb = "PATCH" if current else "POST"
    run(["gh", "api", "-X", verb, f"repos/{OWNER}/{REPO}/pages",
         "-f", f"source[branch]={BRANCH}", "-f", f"source[path]=/{PAGES_DIR}"])
    print(f"    Pages set to {want}" + (f" (was {current})" if current else ""))


def wait_for_live(timeout=300, dry=False):
    step(f"waiting for {URL}")
    if dry:
        print("    would poll until it answers 200")
        return
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(URL, timeout=15) as r:
                if r.status == 200:
                    print(f"    live: {URL}")
                    return
        except Exception:
            pass
        time.sleep(10)
    print(f"    still not answering after {timeout}s -- a first build can take "
          f"a few minutes; check {URL} and the repo's Actions tab")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-m", "--message", help="commit message")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the steps without changing anything")
    ap.add_argument("--no-wait", action="store_true",
                    help="do not poll the published URL at the end")
    args = ap.parse_args()

    data = preflight()
    stamp = build_docs(dry=args.dry_run)
    ensure_repo(dry=args.dry_run)
    msg = args.message or (
        f"Publish {len(data['people'])} researchers across "
        f"{len(data['countries'])} countries ({stamp})")
    pushed = commit_and_push(msg, dry=args.dry_run)
    ensure_pages(dry=args.dry_run)
    if pushed and not args.no_wait:
        wait_for_live(dry=args.dry_run)
    print(f"\n{URL}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as e:
        print(f"\nABORTED: {e}", file=sys.stderr)
        sys.exit(1)
