"""Minimal, dependency-free BibTeX reader shared by the CV and website tooling.

The same file lives in LaTeX/CV/tools/bib.py and christopheryou.github.io/tools/bib.py;
keep them identical.
"""
import re

ME_FAMILY = "You"
ME_GIVEN_INITIAL = "C"

STATUS_LABELS = {
    "inpreparation": "In preparation",
    "submitted": "In submission",
    "inreview": "In review",
    "forthcoming": "To appear",
}


def _read_value(s, i):
    """Read a field value starting at s[i]; return (value, next_index)."""
    if s[i] == "{":
        depth, j = 0, i
        while j < len(s):
            if s[j] == "{" and s[j - 1] != "\\":
                depth += 1
            elif s[j] == "}" and s[j - 1] != "\\":
                depth -= 1
                if depth == 0:
                    return s[i + 1:j], j + 1
            j += 1
        raise ValueError("unbalanced braces near: " + s[i:i + 60])
    if s[i] == '"':
        j = s.index('"', i + 1)
        return s[i + 1:j], j + 1
    m = re.match(r"[^,}\s]+", s[i:])
    return m.group(0), i + m.end()


def parse(path):
    """Return a list of entries: {"type", "key", "order", <lowercased fields>...}."""
    text = open(path, encoding="utf-8").read()
    # Drop full-line % comments so they can mention anything.
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("%"))
    entries, pos = [], 0
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        if m.start() < pos:
            continue
        e = {"type": m.group(1).lower(), "key": m.group(2), "order": len(entries)}
        i = m.end()
        while True:
            fm = re.compile(r"\s*([A-Za-z][\w-]*)\s*=\s*").match(text, i)
            if not fm:
                break
            val, i = _read_value(text, fm.end())
            e[fm.group(1).lower()] = re.sub(r"\s+", " ", val).strip()
            cm = re.compile(r"\s*,?").match(text, i)
            i = cm.end()
        close = text.index("}", i)
        pos = close + 1
        entries.append(e)
    return entries


def keywords(e):
    return [k.strip().lower() for k in e.get("keywords", "").split(",") if k.strip()]


def category(e):
    for k in keywords(e):
        if k in ("journal", "conference", "poster", "mentored"):
            return k
    return "other"


def status(e):
    return e.get("pubstate", "").strip().lower()


def is_published(e):
    return status(e) in ("", "forthcoming")


def sort_key(e):
    """Newest first; forthcoming before dated work; unpublished work last."""
    st = status(e)
    group = 0 if st in ("", "forthcoming") else 1
    year = int(e["year"]) if e.get("year", "").isdigit() else 9999
    month = int(e["month"]) if e.get("month", "").isdigit() else 0
    return (group, -year, -month, e["order"])


# --- names -------------------------------------------------------------------

def split_names(field):
    return [n.strip() for n in re.split(r"\s+and\s+", field) if n.strip()]


def parse_name(n):
    """Return (family, given) from 'Family, Given' or 'Given Family'."""
    n = n.replace("{", "").replace("}", "")
    if "," in n:
        fam, giv = n.split(",", 1)
        return fam.strip(), giv.strip()
    parts = n.split()
    return parts[-1], " ".join(parts[:-1])


def initials(given):
    out = []
    for part in given.replace(".", ". ").split():
        sub = [p for p in part.split("-") if p]
        out.append("-".join(p[0] + "." for p in sub))
    return " ".join(out)


def is_me(family, given):
    return family == ME_FAMILY and given[:1] == ME_GIVEN_INITIAL


def short_name(n):
    fam, giv = parse_name(n)
    return fam, (fam + ", " + initials(giv)).strip().rstrip(","), is_me(fam, giv)


# --- text cleanup --------------------------------------------------------------

_ACCENTS = {r"\"o": "ö", r"\"u": "ü", r"\"a": "ä", r"\'e": "é", r"\'a": "á", r"\~n": "ñ"}


def plain(s):
    """LaTeX-ish field value -> plain text."""
    for k, v in _ACCENTS.items():
        s = s.replace("{" + k + "}", v).replace(k, v)
    s = re.sub(r"\\(textit|textbf|emph|textsc)\{([^{}]*)\}", r"\2", s)
    s = s.replace(r"\&", "&").replace("---", "—").replace("--", "–").replace("~", " ")
    s = s.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", s).strip()


def sentence_case(title):
    """Capitalize the first letter and the first letter after a colon; keep
    everything else (including {Protected} words) exactly as written."""
    t = plain(title)
    t = t[:1].upper() + t[1:]
    return re.sub(r"(:\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)


def venue(e):
    return e.get("journal") or e.get("booktitle") or e.get("publisher") or ""
