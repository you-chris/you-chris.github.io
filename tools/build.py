"""Build the static site from data/. Standard library only (Python 3.11+).

    python tools/build.py

Reads   data/site.toml, data/news.toml, data/projects.toml, data/publications.bib
Writes  index.html, publications.html, projects.html, news.html, cv.html, 404.html

data/publications.bib is a copy of LaTeX/CV/refs.bib (the site-sync skill copies it).
"""
import datetime as dt
import html
import json
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bib  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

NAV = [("index.html", "Home"), ("publications.html", "Publications"),
       ("projects.html", "Projects"), ("news.html", "News"), ("cv.html", "CV")]
CATEGORIES = [("journal", "Journal articles"), ("conference", "Conference papers"),
              ("poster", "Posters, abstracts & demos"), ("mentored", "Undergraduate-mentored")]
CAT_SHORT = {"journal": "Journal", "conference": "Conference", "poster": "Poster / abstract",
             "mentored": "Mentored"}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
MONTHS_LONG = ("January February March April May June July August September "
               "October November December").split()

e_ = html.escape


def load():
    site = tomllib.loads((DATA / "site.toml").read_text(encoding="utf-8"))
    news = tomllib.loads((DATA / "news.toml").read_text(encoding="utf-8"))["news"]
    projects = tomllib.loads((DATA / "projects.toml").read_text(encoding="utf-8"))["project"]
    pubs = bib.parse(DATA / "publications.bib")
    news.sort(key=lambda n: n["date"], reverse=True)
    return site, news, projects, pubs


def month_label(ym, long=False):
    y, m = ym.split("-")[:2]
    return "%s %s" % ((MONTHS_LONG if long else MONTHS)[int(m) - 1], y)


# --- publications -----------------------------------------------------------------

def author_html(e, limit=8):
    names = [bib.short_name(n) for n in bib.split_names(e.get("author", ""))]
    fmt = lambda n: '<span class="me">%s</span>' % e_(n[1]) if n[2] else e_(n[1])
    if len(names) > limit:
        shown = names[:6]
        me = next((n for n in names if n[2]), None)
        parts = [fmt(n) for n in shown]
        if me and me not in shown:
            parts.append("…")
            parts.append(fmt(me))
        parts.append("…")
        parts.append(fmt(names[-1]))
        return ", ".join(parts)
    parts = [fmt(n) for n in names]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + ", &amp; " + parts[-1]


def venue_html(e):
    ven = bib.plain(bib.venue(e))
    bits = ["<i>%s</i>" % e_(ven)] if ven else []
    if e.get("volume"):
        bits.append(e_(e["volume"]))
    st = bib.status(e)
    if not st and e.get("year"):
        bits.append(e_(e["year"]))
    if e.get("note"):
        bits.append(e_(bib.plain(e["note"])))
    return ", ".join(bits)


BIBTEX_FIELDS = ["title", "author", "journal", "booktitle", "volume", "number", "pages",
                 "publisher", "organization", "address", "year", "month", "doi", "note", "pubstate"]


def bibtex(e):
    lines = ["@%s{%s," % (e["type"], e["key"])]
    lines += ["  %s = {%s}," % (f, e[f]) for f in BIBTEX_FIELDS if e.get(f)]
    return "\n".join(lines) + "\n}"


def pub_html(e, show_cat=False):
    title = e_(bib.sentence_case(e["title"]))
    doi = e.get("doi")
    t = '<a href="https://doi.org/%s">%s</a>' % (e_(doi), title) if doi else title
    st = bib.status(e)
    badge = '<span class="status">%s</span> ' % bib.STATUS_LABELS[st] if st else ""
    cat = '<span class="cat">%s</span> ' % CAT_SHORT.get(bib.category(e), "") if show_cat else ""
    acts = []
    if e.get("pdf"):
        acts.append('<a href="samples/%s">PDF</a>' % e_(e["pdf"]))
    if doi:
        acts.append('<a href="https://doi.org/%s">DOI</a>' % e_(doi))
    acts.append('<button type="button" class="linklike" data-bibtex="bib-%s" aria-expanded="false">BibTeX</button>' % e["key"])
    note = ' <span class="pdfnote">%s</span>' % e_(e["pdfnote"]) if e.get("pdfnote") else ""
    return (
        '<li class="pub" id="%s" data-cat="%s">\n'
        '  <p class="pub-title">%s%s%s</p>\n'
        '  <p class="pub-authors">%s</p>\n'
        '  <p class="pub-venue">%s</p>\n'
        '  <p class="pub-actions">%s%s</p>\n'
        '  <pre class="bibtex" id="bib-%s" hidden>%s</pre>\n'
        '</li>' % (e["key"], bib.category(e), cat, badge, t, author_html(e), venue_html(e),
                   " ".join(acts), note, e["key"], e_(bibtex(e))))


def pubs_by_year(pubs):
    groups = {}
    for p in sorted(pubs, key=bib.sort_key):
        st = bib.status(p)
        label = "In progress" if st in ("inpreparation", "submitted", "inreview") else (
            "Forthcoming" if st == "forthcoming" else p.get("year", "Undated"))
        groups.setdefault(label, []).append(p)
    order = ["Forthcoming"] + sorted([k for k in groups if k.isdigit()], reverse=True) + ["In progress", "Undated"]
    return [(k, groups[k]) for k in order if k in groups]


# --- layout -------------------------------------------------------------------------

def page(site, current, title, body, description=None, extra_head=""):
    nav = "\n".join(
        '<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if href == current else "", label)
        for href, label in NAV)
    full_title = site["name"] if current == "index.html" else "%s · %s" % (title, site["name"])
    desc = e_(description or site["description"])
    url = site["url"].rstrip("/") + "/" + ("" if current == "index.html" else current)
    links = " ".join('<a href="%s">%s</a>' % (e_(l["url"]), e_(l["label"])) for l in site["links"])
    year = dt.date.today().year
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e_(full_title)}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{e_(full_title)}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site['url'].rstrip('/')}/{site['headshot']}">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="images/icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,300;1,6..72,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css">
<script>try{{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{extra_head}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar">
  <div class="wrap topbar-inner">
    <a class="wordmark" href="index.html">{e_(site['name'])}</a>
    <div class="topbar-right">
      <nav aria-label="Main">{nav}</nav>
      <button type="button" class="theme-toggle" aria-label="Toggle dark mode" title="Toggle dark mode">
        <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M4.7 4.7l1.6 1.6M17.7 17.7l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.7 19.3l1.6-1.6M17.7 6.3l1.6-1.6"/></svg>
        <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5a8.5 8.5 0 1 0 11.1 11.1Z"/></svg>
      </button>
    </div>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="footer">
  <div class="wrap footer-inner">
    <p><a href="mailto:{e_(site['email'])}">{e_(site['email'])}</a></p>
    <p class="footer-links">{links}</p>
    <p class="muted">© {year} {e_(site['name'])}</p>
  </div>
</footer>
<script src="assets/site.js" defer></script>
</body>
</html>
"""


def section(label, content, sid=None, more=None):
    more_html = '<p class="more"><a href="%s">%s</a></p>' % more if more else ""
    return ('<section class="band"%s>\n<div class="wrap band-inner">\n<h2 class="band-label">%s</h2>\n'
            '<div class="band-body">\n%s\n%s</div>\n</div>\n</section>'
            % (' id="%s"' % sid if sid else "", label, content, more_html))


# --- pages -----------------------------------------------------------------------------

def news_card(n, pubs_by_key):
    link = n.get("link") or ("publications.html#" + n["paper"] if n.get("paper") in pubs_by_key else None)
    img = ('<img src="%s" alt="" loading="lazy">' % e_(n["image"])) if n.get("image") else ""
    title = e_(n["title"])
    title = '<a href="%s">%s</a>' % (e_(link), title) if link else title
    return ('<li class="card%s">%s<div class="card-body"><time datetime="%s">%s</time>'
            '<h3>%s</h3><p>%s</p></div></li>'
            % (" has-img" if img else "", img, n["date"], month_label(n["date"], long=True), title, n["text"]))


def home(site, news, projects, pubs):
    h = site["hero"]
    by_key = {p["key"]: p for p in pubs}
    imgs = "".join('<img src="%s" alt="%s">' % (e_(src), e_(alt))
                   for src, alt in zip(h["images"], h["image_alts"]))
    hero = f"""<section class="hero">
<div class="wrap hero-inner">
  <div class="chat" aria-label="Introduction">
    <div class="turn agent">
      <img class="avatar" src="{e_(site['headshot'])}" alt="{e_(site['name'])}" width="56" height="56">
      <p class="bubble big">{e_(h['greeting'])}</p>
    </div>
    <p class="bubble user">{e_(h['question'])}</p>
    <div class="turn agent reply">
      <span class="avatar-space" aria-hidden="true"></span>
      <div>
        <p class="bubble typing" aria-hidden="true"><span></span><span></span><span></span></p>
        <p class="bubble answer">{e_(h['answer'])}</p>
      </div>
    </div>
    <p class="chips">
      <a class="chip solid" href="{e_(site['cv_pdf'])}">Download my CV</a>
      <a class="chip" href="publications.html">See publications</a>
      <a class="chip" href="mailto:{e_(site['email'])}">Email me</a>
    </p>
  </div>
  <div class="mosaic">{imgs}</div>
</div>
</section>"""

    about = "\n".join("<p>%s</p>" % p for p in site["about"])
    about = f"""<div class="about">
<div class="about-text">
<p class="lede">{e_(site['role'])}, <a href="{e_(site['affiliation_url'])}">{e_(site['affiliation'])}</a>.</p>
{about}
</div>
<figure class="boba"><img src="images/boba-circle.webp" alt="Illustration of Boba, a gray and white cat, at a laptop" width="560" height="560" loading="lazy"><figcaption>Boba, head of code review</figcaption></figure>
</div>"""

    cards = '<ul class="cards">%s</ul>' % "".join(news_card(n, by_key) for n in news[:3])
    selected = [p for p in sorted(pubs, key=bib.sort_key) if "selected" in bib.keywords(p)]
    sel = '<ul class="pubs">%s</ul>' % "\n".join(pub_html(p, show_cat=True) for p in selected)
    feat = [p for p in projects if p.get("featured")]
    proj = '<ul class="tiles">%s</ul>' % "".join(
        '<li><a href="projects.html#%s"><img src="%s" alt="" loading="lazy"><span class="tile-title">%s</span>'
        '<span class="tile-text">%s</span></a></li>' % (p["slug"], e_(p["image"]), e_(p["title"]), e_(p["summary"]))
        for p in feat)

    person = {"@context": "https://schema.org", "@type": "Person", "name": site["name"],
              "jobTitle": site["role"], "affiliation": {"@type": "Organization", "name": site["affiliation"]},
              "email": "mailto:" + site["email"], "url": site["url"], "image": site["url"].rstrip("/") + "/" + site["headshot"],
              "sameAs": [l["url"] for l in site["links"]]}
    head = '<script type="application/ld+json">%s</script>\n' % json.dumps(person)
    body = "\n".join([hero,
                      section("About", about, "about"),
                      section("News", cards, "news", ("news.html", "All news")),
                      section("Selected publications", sel, "publications", ("publications.html", "All publications")),
                      section("Projects", proj, "projects", ("projects.html", "All projects"))])
    return page(site, "index.html", "Home", body, extra_head=head)


def publications(site, pubs):
    counts = {c: sum(1 for p in pubs if bib.category(p) == c) for c, _ in CATEGORIES}
    filters = ['<button type="button" class="filter" aria-pressed="true" data-filter="all">All <span>%d</span></button>' % len(pubs)]
    filters += ['<button type="button" class="filter" aria-pressed="false" data-filter="%s">%s <span>%d</span></button>'
                % (c, label, counts[c]) for c, label in CATEGORIES if counts[c]]
    groups = "\n".join(
        '<section class="year-group">\n<h2 class="year">%s</h2>\n<ul class="pubs">\n%s\n</ul>\n</section>'
        % (label, "\n".join(pub_html(p, show_cat=True) for p in items))
        for label, items in pubs_by_year(pubs))
    body = f"""<div class="wrap page-head">
<h1>Publications</h1>
<p class="muted">My name is highlighted in each author list. PDFs are author copies; DOIs link to the published versions. Also on <a href="{e_(site['links'][0]['url'])}">Google Scholar</a>.</p>
<div class="filters" role="group" aria-label="Filter by type">{''.join(filters)}</div>
</div>
<div class="wrap pub-list" data-pub-list>
{groups}
</div>"""
    return page(site, "publications.html", "Publications", body,
                description="Publications by %s: journal articles, conference papers, posters and abstracts." % site["name"])


def projects_page(site, projects, pubs):
    by_key = {p["key"]: p for p in pubs}
    items = []
    for i, p in enumerate(projects):
        tags = "".join('<span class="tag">%s</span>' % e_(t) for t in p.get("tags", []))
        years = [int(y) for y in re.findall(r"(?:19|20)\d\d", p.get("dates", ""))] or [0]
        end = dt.date.today().year + 1 if "present" in p.get("dates", "").lower() else max(years)
        data = 'data-order="%d" data-start="%d" data-end="%d" data-tags="%s"' % (
            i, min(years), end, e_("|".join(p.get("tags", []))))
        links = "".join('<a href="%s">%s</a>' % (e_(l["url"]), e_(l["label"])) for l in p.get("links", []))
        video = ""
        if p.get("video"):
            vid = e_(p["video"])
            video = ('<button type="button" class="video" data-video="%s">'
                     '<img src="https://i.ytimg.com/vi/%s/hqdefault.jpg" alt="" loading="lazy">'
                     '<span>Play video</span></button>' % (vid, vid))
        papers = [by_key[k] for k in p.get("papers", []) if k in by_key]
        plist = ""
        if papers:
            plist = '<div class="related"><h3>Papers</h3><ul>%s</ul></div>' % "".join(
                '<li><a href="publications.html#%s">%s</a> <span class="muted">%s</span></li>'
                % (q["key"], e_(bib.sentence_case(q["title"])),
                   e_(bib.STATUS_LABELS.get(bib.status(q), q.get("year", "")))) for q in papers)
        items.append(f"""<article class="project" id="{p['slug']}" {data}>
<div class="project-media"><img src="{e_(p['image'])}" alt="" loading="lazy">{video}</div>
<div class="project-text">
  <p class="project-meta"><span>{e_(p.get('dates', ''))}</span>{tags}</p>
  <h2>{e_(p['title'])}</h2>
  <p class="project-sub">{e_(p.get('subtitle', ''))}</p>
  <p>{e_(p['description'])}</p>
  <p class="tech"><span class="muted">Built with</span> {e_(p.get('tech', ''))}</p>
  {'<p class="project-links">' + links + '</p>' if links else ''}
  {plist}
</div>
</article>""")
    all_tags = []
    for p in projects:
        all_tags += [t for t in p.get("tags", []) if t not in all_tags]
    chips = ['<button type="button" class="filter" aria-pressed="true" data-tag-filter="all">All <span>%d</span></button>'
             % len(projects)]
    chips += ['<button type="button" class="filter" aria-pressed="false" data-tag-filter="%s">%s <span>%d</span></button>'
              % (e_(t), e_(t), sum(t in p.get("tags", []) for p in projects)) for t in all_tags]
    controls = ('<div class="controls"><div class="filters" role="group" aria-label="Filter by topic">%s</div>'
                '<label class="sort">Sort by <select data-project-sort>'
                '<option value="featured">Featured</option><option value="newest">Newest</option>'
                '<option value="oldest">Oldest</option></select></label></div>' % "".join(chips))
    body = ('<div class="wrap page-head"><h1>Projects</h1>%s</div>\n'
            '<div class="wrap projects" data-project-list>\n%s\n</div>' % (controls, "\n".join(items)))
    return page(site, "projects.html", "Projects", body,
                description="Research projects by %s on virtual agents, AI, and virtual reality for health." % site["name"])


def news_page(site, news, pubs):
    by_key = {p["key"]: p for p in pubs}
    years = {}
    for n in news:
        years.setdefault(n["date"][:4], []).append(n)
    blocks = []
    for y, items in years.items():
        rows = []
        for n in items:
            link = n.get("link") or ("publications.html#" + n["paper"] if n.get("paper") in by_key else None)
            t = e_(n["title"])
            t = '<a href="%s">%s</a>' % (e_(link), t) if link else t
            rows.append('<li><time datetime="%s">%s</time><div><h3>%s</h3><p>%s</p></div></li>'
                        % (n["date"], MONTHS[int(n["date"][5:7]) - 1], t, n["text"]))
        blocks.append('<section class="year-group"><h2 class="year">%s</h2><ul class="dated">%s</ul></section>'
                      % (y, "".join(rows)))
    body = '<div class="wrap page-head"><h1>News</h1></div>\n<div class="wrap news-list">\n%s\n</div>' % "\n".join(blocks)
    return page(site, "news.html", "News", body)


def cv_page(site):
    cv, res = e_(site["cv_pdf"]), e_(site["resume_pdf"])
    body = f"""<div class="wrap page-head">
<h1>Curriculum vitae</h1>
<p class="muted">The full CV lists every publication, talk, award, and service role. The resume is a two-page summary.</p>
<p class="chips"><a class="chip solid" href="{cv}">Download CV (PDF)</a> <a class="chip" href="{res}">Download resume (PDF)</a></p>
</div>
<div class="wrap"><iframe class="pdf" src="{cv}#view=FitH" title="Curriculum vitae (PDF)"></iframe></div>"""
    return page(site, "cv.html", "CV", body)


def not_found(site):
    body = """<div class="wrap page-head lost">
<img src="images/boba-desk.webp" alt="Illustration of Boba the cat at a laptop" width="720" height="720">
<div><h1>Page not found</h1>
<p>Boba checked everywhere. That page moved when the site was rebuilt. Try the <a href="index.html">home page</a>, <a href="publications.html">publications</a>, or <a href="cv.html">CV</a>.</p></div>
</div>"""
    return page(site, "404.html", "Not found", body)


def cv_archive():
    """Unlinked, noindex list of CV/resume PDFs that were live on the old site (archive/cvs/)."""
    files = sorted((ROOT / "archive" / "cvs").glob("*.pdf"), key=lambda f: f.name.lower())
    rows = "\n".join('<li><a href="cvs/%s">%s</a></li>' % (e_(f.name), e_(f.name)) for f in files)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>CV archive</title>
<link rel="stylesheet" href="../assets/site.css"></head>
<body><main class="wrap page-head"><h1>CV archive</h1>
<p class="muted">Earlier CV and resume PDFs that were live on this site. The current CV is on the <a href="../cv.html">CV page</a>.</p>
<ul class="archive-list">
{rows}
</ul></main></body></html>
"""


def check(site, news, projects, pubs):
    keys = {p["key"] for p in pubs}
    problems = []
    for n in news:
        if n.get("paper") and n["paper"] not in keys:
            problems.append("news '%s': unknown paper key %s" % (n["title"], n["paper"]))
        if n.get("image") and not (ROOT / n["image"]).exists():
            problems.append("news '%s': missing image %s" % (n["title"], n["image"]))
    for p in projects:
        for k in p.get("papers", []):
            if k not in keys:
                problems.append("project %s: unknown paper key %s" % (p["slug"], k))
        if not (ROOT / p["image"]).exists():
            problems.append("project %s: missing image %s" % (p["slug"], p["image"]))
    for p in pubs:
        if p.get("pdf") and not (ROOT / "samples" / p["pdf"]).exists():
            problems.append("publication %s: missing samples/%s" % (p["key"], p["pdf"]))
        if bib.category(p) == "other":
            problems.append("publication %s: no category keyword" % p["key"])
    for f in (site["cv_pdf"], site["resume_pdf"], site["headshot"]):
        if not (ROOT / f).exists():
            problems.append("missing file %s" % f)
    return problems


def main():
    site, news, projects, pubs = load()
    problems = check(site, news, projects, pubs)
    for p in problems:
        print("WARNING:", p)
    out = {"index.html": home(site, news, projects, pubs),
           "publications.html": publications(site, pubs),
           "projects.html": projects_page(site, projects, pubs),
           "news.html": news_page(site, news, pubs),
           "cv.html": cv_page(site),
           "404.html": not_found(site)}
    if (ROOT / "archive" / "cvs").is_dir():
        out["archive/index.html"] = cv_archive()
    for name, text in out.items():
        (ROOT / name).write_text(text, encoding="utf-8", newline="\n")
    print("built %d pages: %d publications, %d news items, %d projects%s"
          % (len(out), len(pubs), len(news), len(projects), "" if not problems else " (%d warnings)" % len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
