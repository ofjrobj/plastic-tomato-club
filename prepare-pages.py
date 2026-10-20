#!/usr/bin/env python3
"""Package generated pages and local assets, checking all internal destinations."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import shutil


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "_site"
manifest = json.loads((ROOT / "content.json").read_text())
files = ["index.html", "styles.css", "project-book.css", "site.js", "favicon.svg", "ornament.png", "robots.txt", ".nojekyll"]
directories = ["assets", "2025"] + [project["slug"] for project in manifest["projects"]]
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)
OUTPUT.mkdir()
for name in files:
    shutil.copy2(ROOT / name, OUTPUT / name)
for name in directories:
    path = Path(name)
    if path.is_absolute() or len(path.parts) != 1 or name in (".", ".."):
        raise ValueError(f"Invalid output directory: {name}")
    shutil.copytree(ROOT / name, OUTPUT / name)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        for attribute in ("href", "src", "poster"):
            if value := attributes.get(attribute):
                self.urls.append(value)


errors = []
html_files = sorted(OUTPUT.rglob("*.html"))
for page in html_files:
    links = Links()
    links.feed(page.read_text())
    for url in links.urls:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        if parsed.path.startswith("/"):
            errors.append(f"{page.relative_to(OUTPUT)}: root-relative URL {url}")
            continue
        target = (page.parent / unquote(parsed.path)).resolve()
        if not target.is_relative_to(OUTPUT):
            errors.append(f"{page.relative_to(OUTPUT)}: URL escapes artifact: {url}")
        elif not target.exists():
            errors.append(f"{page.relative_to(OUTPUT)}: missing local destination {url}")
        elif target.is_dir() and not (target / "index.html").is_file():
            errors.append(f"{page.relative_to(OUTPUT)}: missing directory index {url}")

expected_assets = {Path(asset["local_path"]).name for asset in manifest["assets"]}
actual_assets = {file.name for file in (OUTPUT / "assets").iterdir() if file.is_file()}
if expected_assets != actual_assets:
    errors.append("Public asset inventory differs from the manifest")
if errors:
    raise RuntimeError("Public artifact validation failed:\n" + "\n".join(errors))
print(f"Verified {len(html_files)} pages and {len(actual_assets)} media files in _site/.")
