# christopher.you

Personal website, served by GitHub Pages from `main`. The HTML pages are generated; edit the data and rebuild.

```
data/site.toml          name, links, home-page conversation, About text
data/news.toml          news items
data/projects.toml      projects
data/publications.bib   copy of LaTeX/CV/refs.bib (don't edit here)
tools/build.py          builds index/publications/projects/news/cv/404.html + archive/index.html (Python 3.11+, no packages)
archive/cvs/            CV/resume PDFs that were live before (listed, unlinked, at /archive/)
assets/site.css|js      design and small enhancements
```

```
python tools/build.py
python -m http.server 8765   # preview at http://localhost:8765
```

In Claude Code: `/site-sync` updates the site, `/cv-update` updates the CV, `/academic-update` does both.
