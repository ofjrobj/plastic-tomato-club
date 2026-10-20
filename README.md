# Plastic Tomato Club

An independent static archive of the Plastic Tomato Club projects, July 2025–April 2026. The content and project order were migrated from the existing public archive. Images and videos are served from this repository after the initial import.

## Build locally

Requires Python 3.12 or newer.

```sh
python -m pip install -r requirements-bootstrap.txt
python bootstrap-assets.py
python build.py --manifest content.json
python prepare-pages.py
python -m http.server --directory _site 8000
```

The first import downloads only the media URLs recorded in `content.json`, creates WebP images at quality 88 with a maximum edge of 1920 pixels, and preserves MP4 files. It writes `assets-web/` and a SHA-256 inventory in `asset-lock.json`. Later builds validate those committed files without downloading them again.

`python bootstrap-assets.py --check` verifies the full inventory without network access. `prepare-pages.py` checks local links and media before packaging `_site/`.

## Publish

GitHub Pages uses **GitHub Actions** as its source. A push to `main` builds and deploys the archive; the workflow can also be run manually.

On its first run, the workflow commits the imported `assets-web/` files and checksum lock using the repository's automatic `GITHUB_TOKEN`. This token's push does not trigger another push workflow. Subsequent runs use the media already stored in GitHub. No personal access token is required.

Generated HTML, `assets/`, and `_site/` are excluded from Git. Edit `build.py`, `styles.css`, `site.js`, and `content.json` to change the site. The public artifact includes `noindex` metadata and `robots.txt`.

## Content rights

Artwork, photography, video, text, and project identities remain the property of their respective rights holders. Publishing this archive does not grant an open-source license to its creative content.
