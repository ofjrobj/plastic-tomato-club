#!/usr/bin/env python3
"""Import the observed public media once; later builds use committed files."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import argparse
import json
import os
import re
import shutil
import sys
import time

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
ALLOWED_HOSTS = {"images.spr.so", "assets.super.so"}
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
TRANSFORM = {"format": "WebP", "max_edge": 1920, "quality": 88, "method": 6}


def digest(path):
    with path.open("rb") as stream:
        return sha256(stream.read()).hexdigest()


def asset_path(root, asset):
    expected_suffix = ".webp" if asset["type"] == "image" else ".mp4"
    if not re.fullmatch(r"[a-f0-9]{14}", asset["id"]):
        raise ValueError("Unexpected asset ID")
    path = PurePosixPath(asset["local_path"])
    if path != PurePosixPath("assets-web", asset["id"] + expected_suffix):
        raise ValueError(f"Unexpected local path for {asset['id']}")
    destination = root / path
    if destination.is_symlink() or (root / "assets-web").is_symlink():
        raise ValueError("Asset symlinks are not supported")
    return destination


def inspect(path, asset):
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Missing or empty file")
    if path.stat().st_size >= MAX_DOWNLOAD_BYTES:
        raise ValueError("File exceeds the per-asset size limit")
    if asset["type"] == "image":
        with Image.open(path) as image:
            if image.format != "WEBP":
                raise ValueError("Expected a WebP image")
            image.load()
            if min(image.size) < 1 or max(image.size) > 1920:
                raise ValueError("Invalid optimized image dimensions")
            expected = (asset.get("width"), asset.get("height"))
            if all(expected) and image.size != expected:
                raise ValueError(f"Image dimensions {image.size} differ from {expected}")
    else:
        with path.open("rb") as stream:
            if stream.read(12)[4:8] != b"ftyp":
                raise ValueError("Expected an MP4 file")
        if asset.get("bytes") and path.stat().st_size != asset["bytes"]:
            raise ValueError("MP4 size differs from the audited source")
    return {"path": asset["local_path"], "bytes": path.stat().st_size, "sha256": digest(path)}


def download(url, target):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only the observed public media hosts are allowed")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
    with urlopen(request, timeout=60) as response:
        if urlsplit(response.url).hostname not in ALLOWED_HOSTS:
            raise ValueError("Unexpected download redirect")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) >= MAX_DOWNLOAD_BYTES:
            raise ValueError("Download exceeds the per-asset size limit")
        size = 0
        with target.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size >= MAX_DOWNLOAD_BYTES:
                    raise ValueError("Download exceeds the per-asset size limit")
                stream.write(chunk)
        if not size or (declared and size != int(declared)):
            raise ValueError("Incomplete download")


def ensure_asset(root, asset, previous, check_only):
    destination = asset_path(root, asset)
    if destination.exists():
        result = inspect(destination, asset)
        if previous and result != previous:
            raise ValueError("Committed asset does not match its checksum lock")
        return result, False
    if check_only:
        raise ValueError("Asset is missing; offline validation cannot download it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = asset["display_source"] if asset["type"] == "image" else asset["source_url"]
    for attempt in range(1, 5):
        try:
            with TemporaryDirectory(prefix=".import-", dir=destination.parent) as temporary:
                raw = Path(temporary) / "source"
                output = Path(temporary) / destination.name
                download(source, raw)
                if asset["type"] == "image":
                    with Image.open(raw) as image:
                        image = ImageOps.exif_transpose(image)
                        image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                        if image.mode not in ("RGB", "RGBA"):
                            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
                        image.save(output, "WEBP", quality=88, method=6)
                else:
                    shutil.copyfile(raw, output)
                result = inspect(output, asset)
                if previous and result != previous:
                    raise ValueError("Re-import differs from the committed checksum lock")
                os.replace(output, destination)
                return result, True
        except Exception as error:
            if attempt == 4:
                raise RuntimeError(f"Import failed after {attempt} attempts: {error}") from error
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "content.json")
    parser.add_argument("--check", action="store_true", help="Validate committed files without network access")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text())
    assets = manifest["assets"]
    if not assets:
        raise ValueError("The asset manifest is empty")
    if len({asset["id"] for asset in assets}) != len(assets):
        raise ValueError("The manifest contains duplicate asset IDs")
    if any(asset["type"] not in ("image", "video") for asset in assets):
        raise ValueError("Unsupported media type")
    lock_path = root / "asset-lock.json"
    previous = json.loads(lock_path.read_text())["assets"] if lock_path.exists() else {}
    if args.check and not previous:
        raise ValueError("asset-lock.json is required for offline validation")
    results, failures, downloaded = {}, [], 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = {
            executor.submit(ensure_asset, root, asset, previous.get(asset["id"]), args.check): asset
            for asset in assets
        }
        for future in as_completed(tasks):
            asset = tasks[future]
            try:
                result, imported = future.result()
                results[asset["id"]] = result
                downloaded += int(imported)
            except Exception as error:
                failures.append(f"{asset['id']}: {error}")
    if failures:
        raise RuntimeError("Asset validation failed:\n" + "\n".join(failures))
    if len(results) != len(assets):
        raise RuntimeError("Incomplete asset inventory")
    if args.check:
        if set(previous) != set(results):
            raise ValueError("The checksum lock does not cover exactly the manifest assets")
    else:
        lock = {"version": 1, "transform": TRANSFORM, "assets": dict(sorted(results.items()))}
        lock_text = json.dumps(lock, indent=2, sort_keys=True) + "\n"
        if not lock_path.exists() or lock_path.read_text() != lock_text:
            temporary = lock_path.with_suffix(".json.tmp")
            temporary.write_text(lock_text)
            temporary.replace(lock_path)
    print(f"Validated {len(results)} media files; imported {downloaded}; "
          f"total {sum(item['bytes'] for item in results.values()):,} bytes.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
