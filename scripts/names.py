"""Canonical person names for the ERC datahub PI field.

The datahub writes principal investigators as one free-text string with no
separator between family and given names, in mutually inconsistent conventions:

    'LEHTINEN Jaakko Tapani'   family name in caps, family name first (~6.2k)
    'Oulasvirta Antti Olavi'   no caps at all,      family name first (~8.0k)
    'Daniel Cremers'           no caps at all,      family name LAST  (minority)

Left unresolved, the third case splits one researcher into two: 'Cremers
Daniel' and 'Daniel Cremers' each carried their own ERC millions in a first cut
of this dataset.  Multi-token family names ('Guldstrand Larsen Kim', 'Antonio
J. Pena Monferrer') break a naive first-token rule in the other direction.

Approach: the ~6.2k strings whose capitalisation makes the split unambiguous
are used to learn two lexicons -- which tokens act as family names, and which
act as given names.  Every candidate split of an ambiguous string is then
scored against both, and the better-attested reading wins; ties go to
family-name-first, the majority convention.  A person is keyed on
(family name, first given initial) so middle names do not fork the identity.
"""
import re, unicodedata
from collections import Counter

# weight on family-name evidence relative to given-name evidence
W_FAMILY = 1.0

# nobiliary/patronymic particles bind to the token that follows them, so that
# 'van der Helm' is considered as one family-name unit and never split apart
PARTICLES = {"van", "von", "de", "del", "della", "di", "da", "dos", "der", "den",
             "ter", "le", "la", "el", "al", "bin", "ben", "abu", "vander"}


def group(toks):
    """Merge particle runs with the following token: ['van','der','helm'] -> ['van der helm']."""
    out, buf = [], []
    for t in toks:
        if t in PARTICLES:
            buf.append(t)
        else:
            out.append(" ".join(buf + [t])); buf = []
    if buf:
        out.append(" ".join(buf))
    return out


def pairs(raw):
    """[(display token, ascii-folded token)] with initials dropped, particles grouped.

    Matching and scoring run on the folded form, but what is shown to a reader
    keeps the person's own spelling: 'Kovacs' is not an acceptable rendering of
    'Kovács'.
    """
    out, buf = [], []
    for tok in re.split(r"\s+", (raw or "").strip()):
        disp = tok.strip(" ,.;()")
        n = norm(disp)
        if not n or len(n[0]) < 2:          # initials such as 'J.' carry no identity
            continue
        low = " ".join(n)
        if low in PARTICLES:
            buf.append((disp, low))
        else:
            out.append((" ".join(d for d, _ in buf + [(disp, low)]),
                        " ".join(l for _, l in buf + [(disp, low)])))
            buf = []
    if buf:
        out.append((" ".join(d for d, _ in buf), " ".join(l for _, l in buf)))
    return out


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z' -]", " ", s).lower().split()


def caps_prefix(raw):
    """The leading ALL-CAPS block, when the string has one and is not all caps."""
    t = (raw or "").split()
    if not t or all(x.isupper() for x in t):
        return None
    n = 0
    while n < len(t) and t[n].isupper() and len(t[n]) > 1:
        n += 1
    return " ".join(t[:n]) if n else None


def build_lexicons(raw_strings):
    """Learn (family-name, given-name) token counts from the unambiguous strings."""
    fam, giv = Counter(), Counter()
    for raw in raw_strings:
        cp = caps_prefix(raw)
        if not cp:
            continue
        fam_toks = norm(cp)
        fam[" ".join(fam_toks)] += 1
        if len(fam_toks) > 1:            # avoid double-counting single-token names
            for t in fam_toks:
                fam[t] += 1
        for t in norm(raw):
            if len(t) > 1 and t not in fam_toks:
                giv[t] += 1
    return fam, giv


def _score(fam_toks, giv_toks, fam, giv):
    s = W_FAMILY * fam.get(" ".join(fam_toks), 0)
    for t in giv_toks:
        s += giv.get(t, 0) - fam.get(t, 0)
    return s


def _show(units):
    """Render display tokens, title-casing only the ones the source SHOUTED."""
    out = []
    for disp, _ in units:
        out.append(" ".join(w if not w.isupper() or len(w) == 1 else w.capitalize()
                            for w in disp.split()))
    return " ".join(out)


def parse(raw, fam, giv):
    """Split one PI string into family and given names, keeping its own spelling."""
    units = pairs(raw)
    if not units:
        return None
    if len(units) == 1:
        return {"last": _show(units), "first": "", "key": (units[0][1], "")}

    cp = caps_prefix(raw)
    if cp:
        fam_low = set(norm(cp))
        fam_units = [u for u in units if set(u[1].split()) & fam_low]
        giv_units = [u for u in units if u not in fam_units]
        if not fam_units or not giv_units:
            fam_units, giv_units = units[:1], units[1:]
    else:
        best, fam_units, giv_units = None, units[:1], units[1:]
        for i in range(1, len(units)):
            for cand_f, cand_g, front in ((units[:i], units[i:], True),
                                          (units[i:], units[:i], False)):
                sc = _score([u[1] for u in cand_f], [u[1] for u in cand_g], fam, giv)
                tie = (sc, front)            # ties go to family-name-first
                if best is None or tie > best:
                    best, fam_units, giv_units = tie, cand_f, cand_g

    last_low = " ".join(u[1] for u in fam_units)
    return {"last": _show(fam_units), "first": _show(giv_units),
            "key": (last_low, giv_units[0][1][0] if giv_units else "")}


def resolve(raw_strings, fam, giv):
    """Map every raw PI string to a canonical person.

    Keying on (family name, first-given-INITIAL) was too coarse: it fused Laura
    Kovacs with Levente Kovacs, and Marcin Pilipczuk with Michal Pilipczuk --
    distinct researchers.  We therefore key on the full first given name and
    merge two keys only when one given name is a prefix of the other
    ('Alex'/'Alexander', 'Mel'/'Melvyn').  The cost is the opposite error:
    'Andrei'/'Andreas' Sabelfeld stay apart.  Splitting one person in two only
    understates a total; fusing two people would put one person's name on
    another's money, so we take the safer side.
    """
    parsed = {}
    for raw in set(raw_strings):
        p = parse(raw, fam, giv)
        if p:
            first_tok = p["first"].split()[0].lower() if p["first"] else ""
            parsed[raw] = (p, (p["key"][0], first_tok))

    by_family = {}
    for _, (_, key) in parsed.items():
        by_family.setdefault(key[0], set()).add(key[1])

    alias = {}
    for family, firsts in by_family.items():
        for a in sorted(firsts, key=len):          # short names absorb longer ones
            for b in firsts:
                if a != b and len(a) >= 3 and b.startswith(a):
                    alias[(family, b)] = (family, alias.get((family, a), (family, a))[1])

    out = {}
    for raw, (p, key) in parsed.items():
        canon = alias.get(key, key)
        out[raw] = {"key": canon, "last": p["last"], "first": p["first"]}
    return out
