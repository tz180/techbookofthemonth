#!/usr/bin/env python3
"""Build the Tech Book of the Month static site into dist/.

Content lives as plain files:
  content/posts/<slug>.html  - HTML body with YAML front matter
  content/posts/<slug>.md    - Markdown body with YAML front matter (new posts)
  content/pages/<slug>.html  - standalone pages, same format

Front matter fields: title, date (YYYY-MM-DD), slug, tags, categories, cover.

Requires: PyYAML, markdown  (pip install -r requirements.txt)
Output: dist/ - a plain static folder, deployable to GitHub Pages,
Cloudflare Pages, or any static host.
"""
import glob, os, re, shutil, html, urllib.parse, json, sys
from datetime import datetime, date

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install -r requirements.txt")
try:
    import markdown as md_lib
except ImportError:
    sys.exit("The 'markdown' package is required: pip install -r requirements.txt")

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BASE = "https://www.techbookofthemonth.com"

# ---------- content loading ----------
def parse_content_file(path):
    """Return (meta dict, body html). .md bodies are rendered from Markdown."""
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing YAML front matter")
    end = text.index("\n---\n", 4)
    meta = yaml.safe_load(text[4:end]) or {}
    body = text[end + 5:].strip()
    if path.endswith(".md"):
        body = md_lib.markdown(body, extensions=["extra"])
    if not meta.get("slug"):
        meta["slug"] = os.path.splitext(os.path.basename(path))[0]
    d = meta.get("date")
    if isinstance(d, (date, datetime)):
        meta["date"] = d.strftime("%Y-%m-%d")
    return meta, fix_images(body)

# ---------- image repair ----------
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_ATTR = re.compile(r"(?<![-\w])src\s*=", re.IGNORECASE)
_DATA_SRC = re.compile(r'data-src\s*=\s*"([^"]+)"', re.IGNORECASE)
_SRCSET = re.compile(r'srcset\s*=\s*"([^"]+)"', re.IGNORECASE)

def fix_images(body):
    """Squarespace lazy-load <img data-src="..."> tags carry no src attribute
    and only render via Squarespace's JS, which the static site does not have.
    Give every such image a real src (from data-src, else the first srcset
    candidate) so it loads natively."""
    def repl(m):
        tag = m.group(0)
        if _SRC_ATTR.search(tag):
            return tag
        url = None
        dm = _DATA_SRC.search(tag)
        if dm:
            url = dm.group(1)
        else:
            sm = _SRCSET.search(tag)
            if sm:
                url = sm.group(1).split(",")[0].strip().split(" ")[0]
        if not url:
            return tag
        tag = tag.replace('data-load="false"', "")
        return re.sub(r"<img\b", f'<img src="{url}" loading="lazy"', tag,
                      count=1, flags=re.IGNORECASE)
    return _IMG_TAG.sub(repl, body)

def load_posts():
    posts = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content", "posts", "*.html")) +
                       glob.glob(os.path.join(ROOT, "content", "posts", "*.md"))):
        meta, body = parse_content_file(path)
        meta["body"] = body
        meta["dt"] = datetime.strptime(meta["date"], "%Y-%m-%d")
        posts.append(meta)
    posts.sort(key=lambda p: (p["dt"], p["slug"]), reverse=True)
    return posts

def load_pages():
    pages = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content", "pages", "*.html")) +
                       glob.glob(os.path.join(ROOT, "content", "pages", "*.md"))):
        meta, body = parse_content_file(path)
        meta["body"] = body
        pages.append(meta)
    return pages

# ---------- tag URL segments (baked from the original site's sitemap) ----------
_tagmap = json.load(open(os.path.join(ROOT, "tags.json")))
TAG_SEGMENTS = _tagmap["segments"]
TAG_SEG_BY_NORM = _tagmap["by_norm"]

def tag_href(tag):
    seg = TAG_SEG_BY_NORM.get(tag.lower())
    if seg is None:  # brand-new tag: Squarespace-style encoding
        seg = urllib.parse.quote_plus(tag).replace("'", "%27")
    return "/books/tag/" + seg + "/"

def cat_href(cat):
    return "/books/category/" + urllib.parse.quote(cat) + "/"

# ---------- assets: disk names -> web names (URL-decoded, deduped) ----------
def asset_name_map():
    name_map, used = {}, {}
    for fn in sorted(os.listdir(os.path.join(ROOT, "assets"))):
        web = urllib.parse.unquote(fn)
        if web in used:
            stem, ext = os.path.splitext(web)
            web = stem + "__" + used[web] + ext
        used[web] = fn
        name_map[fn] = web
    return name_map

# ---------- templates ----------
NAV = [("Books", "/books/"), ("Archive", "/archive/"), ("About", "/about/"),
       ("Recommend", "/recommend/"), ("Newsletter", "/newsletter/")]

def page(title, content):
    nav = " · ".join(f'<a href="{h}">{t}</a>' for t, h in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Tech Book of the Month</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="site-header">
<div class="site-title"><a href="/">Tech Book of the Month</a></div>
<nav>{nav}</nav>
</header>
<main>
{content}
</main>
<footer class="site-footer">
<p>Tech Book of the Month — a monthly book club for technology, building technology companies, and the history of technology.</p>
</footer>
</body>
</html>
"""

def fmt_date(dt):
    return dt.strftime("%B ") + str(dt.day) + dt.strftime(", %Y")

def excerpt(body, n=240):
    text = re.sub(r"<[^>]+>", " ", body)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0] + "…"

def listing(post_list):
    items = []
    for p in post_list:
        thumb = f'<img class="thumb" src="{p["cover"]}" alt="">' if p.get("cover") else ""
        items.append(f"""<li>{thumb}<h2><a href="/books/{p['slug']}/">{html.escape(p['title'])}</a></h2>
<p class="entry-date">{fmt_date(p['dt'])}</p>
<p class="excerpt">{html.escape(excerpt(p['body']))}</p></li>""")
    return '<ul class="post-list">\n' + "\n".join(items) + "\n</ul>"

def archive_listing(posts):
    out, cur = [], None
    for p in posts:
        key = p["dt"].strftime("%B %Y")
        if key != cur:
            if cur is not None:
                out.append("</ul>")
            out.append(f'<h2 class="archive-month">{key}</h2>\n<ul class="archive-list">')
            cur = key
        thumb = (f'<img class="archive-thumb" src="{p["cover"]}" alt="" loading="lazy">'
                 if p.get("cover") else "")
        out.append(f"""<li class="archive-entry"><a class="archive-link" href="/books/{p['slug']}/">{thumb}<span class="archive-title">{html.escape(p['title'])}</span></a>
<span class="archive-date">{fmt_date(p['dt'])}</span></li>""")
    if cur is not None:
        out.append("</ul>")
    return "\n".join(out)

# ---------- build ----------
def write(relpath, content, generated):
    path = os.path.join(DIST, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    generated.append("/" + relpath[:-len("/index.html")] if relpath.endswith("/index.html")
                     else "/" + relpath)

def main():
    posts = load_posts()
    pages = load_pages()
    print("posts loaded:", len(posts), "| pages loaded:", len(pages))

    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    generated = []

    shutil.copyfile(os.path.join(ROOT, "style.css"), os.path.join(DIST, "style.css"))
    os.makedirs(os.path.join(DIST, "assets"))
    for fn, web in asset_name_map().items():
        shutil.copyfile(os.path.join(ROOT, "assets", fn), os.path.join(DIST, "assets", web))

    # post pages
    for i, p in enumerate(posts):
        cover_html = f'<img class="cover" src="{p["cover"]}" alt="">' if p.get("cover") else ""
        meta_html = ""
        if p.get("categories"):
            links = ", ".join(f'<a href="{cat_href(c)}">{html.escape(c)}</a>' for c in p["categories"])
            meta_html += f'<p class="tags">Filed under: {links}</p>'
        if p.get("tags"):
            links = ", ".join(f'<a href="{tag_href(t)}">{html.escape(t)}</a>' for t in p["tags"])
            meta_html += f'<p class="tags">Tags: {links}</p>'
        nav_links = []
        if i > 0:
            newer = posts[i - 1]
            nav_links.append(f'<a class="newer" href="/books/{newer["slug"]}/">&larr; Newer book: {html.escape(newer["title"])}</a>')
        if i < len(posts) - 1:
            older = posts[i + 1]
            nav_links.append(f'<a class="older" href="/books/{older["slug"]}/">Older book: {html.escape(older["title"])} &rarr;</a>')
        nav_html = ('<nav class="post-nav">' + "\n".join(nav_links) + "</nav>") if nav_links else ""
        content = f"""<article class="post">
<h1>{html.escape(p['title'])}</h1>
<p class="post-date">{fmt_date(p['dt'])}</p>
{cover_html}
{p['body']}
{meta_html}
{nav_html}
</article>"""
        write(f"books/{p['slug']}/index.html", page(p["title"], content), generated)

    # homepage + books index
    intro = ('<p class="intro">A monthly book club for technology, building '
             'technology companies, and the history of technology. One book '
             'a month, written up in full.</p>\n')
    write("index.html", page("Home", "<h1>Tech Book of the Month</h1>\n" + intro + listing(posts)), generated)
    write("books/index.html", page("Books", "<h1>Books</h1>\n" + listing(posts)), generated)

    # tag pages (exact segments from the original sitemap + any new tags)
    segments = list(TAG_SEGMENTS)
    known_norms = set(TAG_SEG_BY_NORM)
    for p in posts:
        for t in p.get("tags") or []:
            if t.lower() not in known_norms:
                seg = urllib.parse.quote_plus(t).replace("'", "%27")
                segments.append(seg)
                TAG_SEG_BY_NORM[t.lower()] = seg
                known_norms.add(t.lower())
    for seg in segments:
        display = urllib.parse.unquote(seg).replace("+", " ")
        matched = [p for p in posts if display.lower() in [t.lower() for t in (p.get("tags") or [])]]
        content = f"<h1>Tag: {html.escape(display)}</h1>\n" + listing(matched)
        write(f"books/tag/{urllib.parse.unquote(seg)}/index.html",
              page(f"Tag: {display}", content), generated)

    # category pages
    cats = sorted({c for p in posts for c in (p.get("categories") or [])})
    for cat in cats:
        matched = [p for p in posts if cat in (p.get("categories") or [])]
        content = f"<h1>Category: {html.escape(cat)}</h1>\n" + listing(matched)
        write(f"books/category/{cat}/index.html", page(f"Category: {cat}", content), generated)

    # standalone pages (archive-style pages get the generated listing appended)
    for pg in pages:
        body = pg["body"]
        if pg["slug"] in ("archive", "new-page"):
            body = body + "\n" + archive_listing(posts)
        write(f"{pg['slug']}/index.html", page(pg["title"], body), generated)

    # sitemap
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for pth in generated:
        if pth.endswith(".xml") or pth.endswith(".css"):
            continue
        loc = BASE + "/" if pth in ("/index.html", "/") else BASE + pth + "/"
        sm.append(f"<url><loc>{loc}</loc></url>")
    sm.append("</urlset>")
    with open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sm) + "\n")

    print("generated paths:", len(generated))

if __name__ == "__main__":
    main()
