"""Canonical display names for host institutions.

The three sources spell the same university three ways: CORDIS supplies either
an all-caps legal name ('JOHANNES KEPLER UNIVERSITAET LINZ') or a terse acronym
('UOXF', 'USAAR'); the FWF gives a German trading name ('Universitaet Linz');
research.fi gives an English one.  Without a mapping, one professor's ERC money
and national money are filed under two different employers.

ALIAS is keyed on the upper-cased source string.  A handful of acronyms are
ambiguous across countries ('UU' is Utrecht in NL and Uppsala in SE, 'AU' is
Aarhus in DK and Aalborg elsewhere), so those are keyed on (country, string).
"""
import re

BY_COUNTRY = {
    ("NL", "UU"): "Utrecht University",
    ("SE", "UU"): "Uppsala University",
    ("DK", "AU"): "Aarhus University",
    ("AT", "UNIVERSITAT LINZ"): "Johannes Kepler University Linz",
    ("AT", "UNIVERSITÄT LINZ"): "Johannes Kepler University Linz",
}

ALIAS = {
    # --- acronyms used by CORDIS ---
    "INRIA": "Inria", "UOXF": "University of Oxford", "TAU": "Tel Aviv University",
    "IST AUSTRIA": "Institute of Science and Technology Austria",
    "TUM": "Technical University of Munich", "MPG": "Max Planck Society",
    "CNRS": "CNRS", "RWTH AACHEN": "RWTH Aachen University",
    "USAAR": "Saarland University", "WEIZMANN": "Weizmann Institute of Science",
    "UEDIN": "University of Edinburgh", "TUB": "TU Berlin",
    "UNIWARSAW": "University of Warsaw", "BIU": "Bar-Ilan University",
    "KTH": "KTH Royal Institute of Technology", "UB": "University of Barcelona",
    "USI": "Università della Svizzera italiana", "BSC CNS": "Barcelona Supercomputing Center",
    "POLIMI": "Politecnico di Milano", "UCPH": "University of Copenhagen",
    "LMU MUENCHEN": "LMU Munich", "LUH": "Leibniz University Hannover",
    "UFR": "University of Freiburg", "EPFL": "EPFL", "ETH ZÜRICH": "ETH Zurich",
    "ETH ZURICH": "ETH Zurich", "KU LEUVEN": "KU Leuven", "UGENT": "Ghent University",
    "UOS": "University of Sussex", "UCL": "University College London",
    "UPF": "Universitat Pompeu Fabra", "UGOT": "University of Gothenburg",
    "CVUT": "Czech Technical University in Prague", "EPFL LAUSANNE": "EPFL",
    # --- long legal names ---
    "THE CHANCELLOR MASTERS AND SCHOLARS OF THE UNIVERSITY OF CAMBRIDGE":
        "University of Cambridge",
    "THE CHANCELLOR MASTERS AND SCHOLARS OF THE UNIVERSITY OF OXFORD":
        "University of Oxford",
    "IMPERIAL COLLEGE OF SCIENCE TECHNOLOGY AND MEDICINE": "Imperial College London",
    "CISPA - HELMHOLTZ-ZENTRUM FUR INFORMATIONSSICHERHEIT GGMBH":
        "CISPA Helmholtz Center for Information Security",
    "THE HEBREW UNIVERSITY OF JERUSALEM": "Hebrew University of Jerusalem",
    "TECHNION - ISRAEL INSTITUTE OF TECHNOLOGY": "Technion",
    "AALTO KORKEAKOULUSAATIO SR": "Aalto University",
    "AALTO-KORKEAKOULUSAATIO SR": "Aalto University",
    "HELSINGIN YLIOPISTO": "University of Helsinki",
    "TAMPEREEN KORKEAKOULUSAATIO SR": "Tampere University",
    "TAMPERE UNIVERSITY": "Tampere University",
    "OULUN YLIOPISTO": "University of Oulu",
    "TURUN YLIOPISTO": "University of Turku",
    "JYVASKYLAN YLIOPISTO": "University of Jyväskylä",
    "TECHNISCHE UNIVERSITÄT WIEN": "TU Wien", "TECHNISCHE UNIVERSITAET WIEN": "TU Wien",
    "TECHNISCHE UNIVERSITÄT GRAZ": "TU Graz", "TECHNISCHE UNIVERSITAET GRAZ": "TU Graz",
    "TECHNISCHE UNIVERSITAT DARMSTADT": "TU Darmstadt",
    "TECHNISCHE UNIVERSITÄT DARMSTADT": "TU Darmstadt",
    "JOHANNES KEPLER UNIVERSITÄT LINZ": "Johannes Kepler University Linz",
    "JOHANNES KEPLER UNIVERSITAET LINZ": "Johannes Kepler University Linz",
    "UNIVERSITÄT WIEN": "University of Vienna", "UNIVERSITAET WIEN": "University of Vienna",
    "UNIVERSITÄT INNSBRUCK": "University of Innsbruck",
    "UNIVERSITÄT SALZBURG": "University of Salzburg",
    "MEDIZINISCHE UNIVERSITÄT WIEN": "Medical University of Vienna",
    "INSTITUTE OF SCIENCE AND TECHNOLOGY AUSTRIA":
        "Institute of Science and Technology Austria",
    "VTT TECHNICAL RESEARCH CENTRE OF FINLAND LTD": "VTT",
}

_SMALL = {"of", "and", "the", "for", "in", "de", "di", "der", "von", "van", "du", "la"}

# long legal names as CORDIS spells them (keys are punctuation-stripped upper case)
ALIAS.update({
    "INSTITUT NATIONAL DE RECHERCHE EN INFORMATIQUE ET AUTOMATIQUE": "Inria",
    "THE CHANCELLOR MASTERS AND SCHOLARS OF THE UNIVERSITY OF OXFORD":
        "University of Oxford",
    "EIDGENOESSISCHE TECHNISCHE HOCHSCHULE ZUERICH": "ETH Zurich",
    "ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE": "EPFL",
    "TECHNISCHE UNIVERSITAET MUENCHEN": "Technical University of Munich",
    "MAX PLANCK GESELLSCHAFT ZUR FORDERUNG DER WISSENSCHAFTEN EV": "Max Planck Society",
    "CENTRE NATIONAL DE LA RECHERCHE SCIENTIFIQUE CNRS": "CNRS",
    "KATHOLIEKE UNIVERSITEIT LEUVEN": "KU Leuven",
    "RHEINISCH WESTFAELISCHE TECHNISCHE HOCHSCHULE AACHEN": "RWTH Aachen University",
    "UNIVERSITAT DES SAARLANDES": "Saarland University",
    "THE UNIVERSITY OF EDINBURGH": "University of Edinburgh",
    "TECHNISCHE UNIVERSITAT BERLIN": "TU Berlin",
    "UNIWERSYTET WARSZAWSKI": "University of Warsaw",
    "BAR ILAN UNIVERSITY": "Bar-Ilan University",
    "KUNGLIGA TEKNISKA HOEGSKOLAN": "KTH Royal Institute of Technology",
    "UNIVERSITA DELLA SVIZZERA ITALIANA": "Universita della Svizzera italiana",
    "BARCELONA SUPERCOMPUTING CENTER CENTRO NACIONAL DE SUPERCOMPUTACION":
        "Barcelona Supercomputing Center",
    "KOBENHAVNS UNIVERSITET": "University of Copenhagen",
    "AARHUS UNIVERSITET": "Aarhus University",
    "LUDWIG MAXIMILIANS UNIVERSITAET MUENCHEN": "LMU Munich",
    "LATVIJAS UNIVERSITATE": "University of Latvia",
    "UNIVERSITAT BASEL": "University of Basel",
    "RUHR UNIVERSITAET BOCHUM": "Ruhr University Bochum",
    "UNIVERSITEIT VAN AMSTERDAM": "University of Amsterdam",
    "TECHNISCHE UNIVERSITEIT DELFT": "TU Delft",
    "UNIVERSITAT POMPEU FABRA": "Universitat Pompeu Fabra",
    "CESKE VYSOKE UCENI TECHNICKE V PRAZE": "Czech Technical University in Prague",
})


def _key(s):
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9ÄÖÜäöüßÀ-ÿ ]", " ", s)).strip().upper()


# keys may have been written with punctuation; index them the same way lookups are made
ALIAS = {_key(k): v for k, v in ALIAS.items()}
BY_COUNTRY = {(c, _key(k)): v for (c, k), v in BY_COUNTRY.items()}


def clean(name, country=None):
    if not name or not isinstance(name, str):
        return ""
    s = re.sub(r"\s+", " ", name).strip()
    # punctuation varies between sources ('Max-Planck-Gesellschaft' vs 'Max Planck
    # Gesellschaft', 'CNRS.' vs 'CNRS'), so match on a punctuation-free key
    up = _key(s)
    if country and (country, up) in BY_COUNTRY:
        return BY_COUNTRY[(country, up)]
    if up in ALIAS:
        return ALIAS[up]
    if len(s) <= 5 and s.isupper():         # a bare acronym reads worse title-cased
        return s
    if s.isupper() or s.islower():          # normalise SHOUTED / lowercase legal names
        words = []
        for i, w in enumerate(s.split()):
            if w.isdigit():
                words.append(w)
            elif w.lower() in _SMALL and i:
                words.append(w.lower())
            else:                            # keep the part after a hyphen capitalised
                words.append("-".join(x.capitalize() for x in w.split("-")))
        s = " ".join(words)
    return s
