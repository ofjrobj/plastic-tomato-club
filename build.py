#!/usr/bin/env python3
"""Build the Plastic Tomato Club archive with Python's standard library."""
from pathlib import Path
from html import escape
from urllib.parse import urlparse
import argparse
import json
import shutil

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--manifest", type=Path, default=ROOT / "content.json")
args = parser.parse_args()
data = json.loads(args.manifest.read_text())
assets = {a["id"]: a for a in data["assets"]}
projects = {p["slug"]: p for p in data["projects"]}
groups = list(reversed(data["groups"]))
ordered = [projects[slug] for group in groups for slug in group["projects"]]
all_ids = []


def e(value):
    return escape(str(value), quote=True)


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))


def first_image(nodes):
    return next(n["asset_id"] for n in walk(nodes) if n["type"] == "image")


def group_id(title):
    return "2026" if title == "2026" else ("2025-fw" if "F/W" in title else "2025-ss")


def season(title):
    return title.replace(" Project", "")


def asset_url(asset_id, base):
    asset = assets[asset_id]
    url = base + "assets/" + Path(asset["local_path"]).name
    # Replaced originals need a new URL so returning visitors see the update.
    revision = asset.get("original_sha256")
    return url + "?v=" + revision[:12] if revision else url


def image_markup(asset_id, base, alt, eager=False, css_class=""):
    asset = assets[asset_id]
    # Actual dimensions avoid layout shifts; the source's width/height can be
    # Notion display dimensions, so only use the audited pixel dimensions.
    w = asset.get("width")
    h = asset.get("height")
    dimensions = f' width="{int(w)}" height="{int(h)}"' if w and h else ""
    loading = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<img class="{css_class}" src="{e(asset_url(asset_id, base))}" alt="{e(alt)}"{dimensions} {loading} decoding="async">'


def shell(title, description, body, base="./", project=False):
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f4f2eb">
  <meta name="robots" content="noindex, nofollow">
  <meta name="description" content="{e(description)}">
  <title>{e(title)} — Plastic Tomato Club</title>
  <link rel="icon" href="{base}favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{base}styles.css">
  <script src="{base}site.js" defer></script>
</head>
<body class="{'project-page' if project else 'archive-page'}">
<a class="skip-link" href="#main">Skip to content</a>
{body}
</body>
</html>
'''


def footer(base="./"):
    return f'''<footer class="site-footer">
    <a class="footer-brand" href="{base}">Plastic Tomato Club</a>
    <p>2025.07–2026.04</p>
    <a href="https://undecember27.wpcomstaging.com/">J Yoon’s portfolio</a>
  </footer>'''


def home():
    cards = []
    for group in groups:
        gid = group_id(group["title"])
        rendered = []
        for i, slug in enumerate(group["projects"]):
            p = projects[slug]
            cover = first_image(p["content"])
            number = ordered.index(p) + 1
            rendered.append(f'''<article class="project-card card-{i % 4}">
              <a href="./{e(slug)}/" class="project-card-link">
                <div class="cover">{image_markup(cover, "./", p["title"], css_class="cover-image")}</div>
                <div class="card-caption"><span class="card-number">{number:02d}</span><h3>{e(p["title"])}</h3><span class="card-season">{e(season(p["season"]))}</span></div>
              </a>
            </article>''')
        cards.append(f'''<section class="season-section" id="{gid}" data-season="{gid}" aria-labelledby="label-{gid}">
          <header class="section-header"><h2 id="label-{gid}">{e(season(group["title"]))}</h2><span>{len(group["projects"]):02d} projects</span></header>
          <div class="project-grid">{''.join(rendered)}</div>
        </section>''')
    hero_id = first_image(data["home"]["content"])
    # This is the original project's announcement, presented in regular case.
    announcement = ("Our project concluded in April, and we are currently discussing a new one. "
                    "In the meantime, we will be sharing our individual projects, so please stay tuned.")
    return shell("Archive", "The Plastic Tomato Club project archive, 2025.07–2026.04. Explore eleven projects across three seasons.", f'''
  <header class="site-header">
    <a class="wordmark" href="./" aria-label="Plastic Tomato Club home">PTC</a>
    <a class="header-archive" href="#archive">Project archive</a>
    <span class="header-period">2025.07–2026.04</span>
  </header>
  <main id="main">
    <section class="home-hero" aria-labelledby="home-title">
      <h1 id="home-title"><span>Plastic</span><span>Tomato Club</span></h1>
      <div class="hero-foot">
        <p class="hero-note">A collection of<br>eleven projects.</p>
        <div class="hero-intro"><p>{announcement}</p><a class="text-link" href="#archive">Browse the archive</a></div>
        <a class="hero-object" href="./red-horse/" aria-label="Explore Year of the Red Horse">{image_markup(hero_id, "./", "Red horse ornament, Plastic Tomato Club", eager=True)}</a>
      </div>
    </section>
    <div class="archive-heading" id="archive"><p>Selected collections</p><nav class="filter-nav" aria-label="Filter projects by season">
      <a href="#all" data-filter="all" aria-current="true">All <span>11</span></a>
      <a href="#2026" data-filter="2026">2026 <span>02</span></a>
      <a href="#2025-fw" data-filter="2025-fw">2025 F/W <span>05</span></a>
      <a href="#2025-ss" data-filter="2025-ss">2025 S/S <span>04</span></a>
    </nav></div>
    <p class="filter-status sr-only" role="status"></p>
    <div class="catalogue">{''.join(cards)}</div>
  </main>
  {footer()}
''')


def project_page(p):
    base = "../"
    counter = [0]

    def render(node, depth=0):
        kind = node["type"]
        if kind in ("image", "video"):
            asset_id = node["asset_id"]
            all_ids.append(asset_id)
            asset = assets[asset_id]
            counter[0] += 1
            num = counter[0]
            caption = asset.get("alt", "")
            if caption.strip().lower() == "image":
                caption = ""
            alt = caption or f'{p["title"]} — image {num:02d}'
            if kind == "image":
                content = f'<a class="image-open" href="{e(asset_url(asset_id, base))}" aria-label="View {e(alt)} full size" data-gallery-image>{image_markup(asset_id, base, alt, eager=num == 1)}</a>'
            else:
                content = f'<video controls playsinline preload="none" aria-label="{e(p["title"])} — video {num:02d}"><source src="{e(asset_url(asset_id, base))}" type="{e(asset.get("mime_type", "video/mp4"))}"><a href="{e(asset_url(asset_id, base))}">Open video</a></video>'
            caption_html = f'<figcaption><span>{num:02d}</span>{e(caption)}</figcaption>' if caption else f'<figcaption class="image-number">{num:02d}</figcaption>'
            return f'<figure class="media-item media-{kind}" data-asset="{asset_id}">{content}{caption_html}</figure>'
        if kind == "group":
            children = node["children"]
            n = len(children)
            columns = 2 if n > 3 else max(n, 1)
            return f'<div class="media-group columns-{columns}" data-original-group="true">{"".join(render(c, depth+1) for c in children)}</div>'
        if kind in ("text", "heading"):
            tag = "h2" if kind == "heading" else "p"
            return f'<{tag} class="gallery-text">{e(node["text"]).replace(chr(10), "<br>")}</{tag}>'
        if kind == "embed":
            source = node.get("source_url", node["url"])
            url = node["url"]
            return f'''<div class="external-media"><iframe src="{e(source)}" title="{e(p["title"])} — Pinterest media" loading="lazy" allowfullscreen></iframe><a class="text-link" href="{e(url)}" target="_blank" rel="noopener noreferrer">View on Pinterest</a></div>'''
        if kind == "link":
            url = node["url"]
            if url.startswith("/") and not url.startswith("//"):
                url = base + url.strip("/") + "/"
            return f'<p class="gallery-text"><a class="text-link" href="{e(url)}">{e(node["text"] or "Project archive")}</a></p>'
        raise ValueError(f"Unknown content node type: {kind}")

    gallery = "\n".join(render(n) for n in p["content"])
    nav = []
    for group in groups:
        links = []
        for slug in group["projects"]:
            other = projects[slug]
            current = ' aria-current="page"' if slug == p["slug"] else ""
            links.append(f'<li><a href="../{e(slug)}/"{current}>{e(other["title"])}</a></li>')
        nav.append(f'<div class="index-group"><p>{e(season(group["title"]))}</p><ul>{"".join(links)}</ul></div>')
    idx = ordered.index(p)
    nextp = ordered[(idx+1) % len(ordered)]
    previous = ordered[(idx-1) % len(ordered)]
    return shell(p["title"], f'{p["title"]}, {season(p["season"])}. A Plastic Tomato Club project.', f'''
    <header class="site-header project-top">
      <a class="wordmark" href="../">Plastic Tomato Club</a>
      <a class="header-archive" href="../#archive">Archive</a>
      <span class="header-period">{e(season(p["season"]))}</span>
    </header>
    <main id="main" class="project-layout">
      <aside class="project-sidebar">
        <details class="project-index" open>
          <summary>Project index</summary>
          <nav aria-label="All projects">{''.join(nav)}</nav>
        </details>
      </aside>
      <article class="project-main">
        <header class="project-title"><span class="project-count">{idx+1:02d} / 11</span><h1>{e(p["title"])}</h1><p>{e(season(p["season"]))}</p></header>
        <div class="project-gallery">{gallery}</div>
        <nav class="project-pagination" aria-label="Adjacent projects">
          <a href="../{e(previous["slug"])}/"><span>Previous project</span>{e(previous["title"])}</a>
          <a href="../{e(nextp["slug"])}/"><span>Next project</span>{e(nextp["title"])}</a>
        </nav>
      </article>
    </main>
    {footer("../")}
    <dialog class="lightbox" aria-label="Image viewer">
      <div class="lightbox-top"><p class="lightbox-label"></p><button type="button" class="lightbox-close">Close</button></div>
      <div class="lightbox-image-wrap"><img class="lightbox-image" alt=""></div>
      <div class="lightbox-bottom"><button type="button" data-lightbox-prev>Previous</button><p class="lightbox-position" aria-live="polite"></p><button type="button" data-lightbox-next>Next</button></div>
    </dialog>
''', base="../", project=True)


(ROOT / "assets").mkdir(exist_ok=True)
for asset in assets.values():
    src = args.manifest.parent / asset["local_path"]
    if not src.is_file():
        raise FileNotFoundError(src)
    dest = ROOT / "assets" / src.name
    if not dest.exists() or dest.stat().st_size != src.stat().st_size or src.stat().st_mtime > dest.stat().st_mtime:
        shutil.copy2(src, dest)

(ROOT / "index.html").write_text(home())
for p in ordered:
    (ROOT / p["slug"]).mkdir(exist_ok=True)
    (ROOT / p["slug"] / "index.html").write_text(project_page(p))
# The original archive path remains useful when old bookmarks are migrated.
(ROOT / "2025").mkdir(exist_ok=True)
(ROOT / "2025/index.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta name="robots" content="noindex, nofollow"><meta http-equiv="refresh" content="0;url=../#archive"><title>Plastic Tomato Club archive</title><a href="../#archive">Open the project archive</a></html>''')
(ROOT / ".nojekyll").touch()
(ROOT / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
(ROOT / "content.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
(ROOT / "build-report.json").write_text(json.dumps({
    "projects": len(ordered), "assets": len(assets),
    "project_media_occurrences": len(all_ids),
    "images": sum(a["type"] == "image" for a in assets.values()),
    "videos": sum(a["type"] == "video" for a in assets.values()),
    "bytes": sum((ROOT / "assets" / Path(a["local_path"]).name).stat().st_size for a in assets.values()),
    "all_project_media_preserved": len(all_ids) == sum(n["type"] in ("image", "video") for p in ordered for n in walk(p["content"])),
}, indent=2))
print((ROOT / "build-report.json").read_text())
