# Tech Book of the Month

The static site behind [techbookofthemonth.com](https://www.techbookofthemonth.com) —
a monthly book club for technology, building technology companies, and the
history of technology. No website builder, no database, no server: just files.

## How the site is structured

```
content/posts/    One file per book post: <slug>.html (older posts) or <slug>.md (new posts)
content/pages/    Standalone pages: about, archive, recommend, newsletter, new-page
assets/           Images (referenced from posts as /assets/<filename>)
build.py          The build script — turns content/ + assets/ into the finished site
dist/             The built site (generated; never edit by hand, not in git)
style.css         The one shared stylesheet
tags.json         URL mapping for tag pages, preserved from the original site
```

Every content file is YAML front matter followed by the post body:

```
---
title: January 2027 - Some Book by Some Author
date: 2027-01-15
slug: jan27
tags: [Example Tag, Another Tag]
categories: [Non-Fiction]
cover: /assets/some-cover.jpg
---
```

`build.py` generates: a page per post at `/books/<slug>/`, the homepage and
`/books/` index (newest first), the archive page, one page per tag at
`/books/tag/<tag>/`, category pages, the standalone pages, and `sitemap.xml`.

## Add a new post

**Option A — do it yourself (about a minute):**

1. Create `content/posts/<slug>.md` — Markdown, with this front matter:

   ```markdown
   ---
   title: January 2027 - Some Book by Some Author
   date: 2027-01-15
   slug: jan27
   tags: [Some Company, Some Theme]
   categories: [Non-Fiction]
   cover:
   ---

   Write the post here in **Markdown**. Links, lists, quotes, and
   headings all work. To include an image, drop the file in `assets/`
   and reference it as `/assets/the-file.jpg`.
   ```

   (`cover:` can be left empty, or point at an image in `assets/` to show
   the book cover at the top of the post and in the indexes.)

2. Commit and push to `main`.
3. GitHub Actions rebuilds the site and deploys it — live in about a minute.

**Option B — don't:** just send the text to Arlo and he'll add the file and push.

## Run the build locally

```bash
pip install -r requirements.txt   # needs Python 3.10+: PyYAML + markdown
python build.py                   # writes the finished site to dist/
```

To preview, serve the folder with any static server, e.g.
`python -m http.server -d dist 8000` and open http://localhost:8000.

## Where it deploys

- **GitHub Pages** — automatic on every push to `main`, via
  `.github/workflows/pages.yml` (build, then deploy `dist/`).
- **Cloudflare Pages** — `dist/` is a plain static folder with no server
  features, so it can be uploaded or connected as-is (build command:
  `pip install -r requirements.txt && python build.py`, output: `dist`).

## Notes

- The 60 original posts were migrated from Squarespace in November 2026 with
  their URLs, tags, and images preserved. Their files are `.html` because
  their bodies are HTML; new posts can be either `.md` or `.html`.
- The old "Choose The Next Book" page was retired in the migration and is
  intentionally not part of this site.
