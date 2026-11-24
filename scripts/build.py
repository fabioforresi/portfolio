#!/usr/bin/env python3
"""Builds the website into ./dist from the simple folders in ./projects.

Usage:
    python scripts/build.py            # build into dist/
    python scripts/build.py --serve    # build, then preview at http://localhost:8000
"""
import argparse
import json
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageOps

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
KNOWN_BUT_UNSUPPORTED = {".heic", ".heif", ".tif", ".tiff", ".gif", ".bmp", ".psd", ".raw", ".cr2", ".nef", ".arw"}
PROJECT_KEYS = {"title", "category", "year", "description", "video", "draft"}
SITE_KEYS = {"name", "tagline", "footer", "logo", "categories", "contact_text", "email", "link"}
MAX_SIDE = 2200     # longest side of gallery images
THUMB_SIDE = 1400   # longest side of thumbnails
QUALITY = 85


class BuildError(Exception):
    """Raised with a list of plain-language problems."""
    def __init__(self, problems):
        super().__init__("\n".join(problems))
        self.problems = problems


# ---------- parsing ----------
def parse_kv(text, keys):
    """Parse 'key: value' text. Lines that don't start with a known key continue the previous value."""
    data, key = {}, None
    for raw in text.lstrip("\ufeff").splitlines():
        if raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.*)$", raw)
        if m and m.group(1).lower() in keys:
            key = m.group(1).lower()
            data.setdefault(key, []).append(m.group(2).strip())
        elif key is not None:
            data[key][-1] += "\n" + raw.rstrip()
    return {k: [v.strip() for v in vals] for k, vals in data.items()}


def first(d, k, default=""):
    return d.get(k, [default])[0]


def video_embed(url):
    """Turn a normal YouTube/Vimeo link into an embeddable one. Returns None if unsupported."""
    u = urlparse(url.strip())
    host = (u.netloc or "").lower().replace("www.", "")
    if host in ("youtube.com", "m.youtube.com"):
        if u.path.startswith("/embed/"):
            return f"https://www.youtube.com/embed/{u.path.split('/')[2]}"
        vid = parse_qs(u.query).get("v", [""])[0]
        return f"https://www.youtube.com/embed/{vid}" if vid else None
    if host == "youtu.be":
        return f"https://www.youtube.com/embed/{u.path.strip('/')}" if u.path.strip("/") else None
    if host == "vimeo.com":
        m = re.match(r"^/(\d+)(?:/([0-9a-f]+))?", u.path)
        if m:
            extra = f"?h={m.group(2)}" if m.group(2) else ""
            return f"https://player.vimeo.com/video/{m.group(1)}{extra}"
    if host == "player.vimeo.com" and u.path.startswith("/video/"):
        return url.strip()
    return None


def slug_name(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "file"


def natural_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


# ---------- site + projects ----------
def load_site(root, problems):
    f = root / "site.txt"
    if not f.exists():
        problems.append("The file 'site.txt' is missing from the main folder.")
        return {"name": "Portfolio", "categories": [], "contact": {}}
    d = parse_kv(f.read_text(encoding="utf-8"), SITE_KEYS)
    cats = [c.strip() for c in first(d, "categories").split(",") if c.strip()]
    if not cats:
        problems.append("site.txt: the line 'categories:' is empty. Example:  categories: Landscape, Street, Travel")
    links = []
    for line in d.get("link", []):
        label, _, url = line.partition("|")
        if url.strip():
            links.append({"label": label.strip(), "url": url.strip()})
        else:
            problems.append(f"site.txt: the link '{line}' must look like:  link: Instagram | https://instagram.com/name")
    return {
        "name": first(d, "name", "Portfolio"),
        "tagline": first(d, "tagline"),
        "footer": first(d, "footer"),
        "logo": first(d, "logo"),
        "categories": cats,
        "contact": {"text": first(d, "contact_text"), "email": first(d, "email"), "links": links},
    }


def optimize(src, dst, max_side):
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((max_side, max_side), Image.LANCZOS)
        ext = dst.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            im.convert("RGB").save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        elif ext == ".png":
            im.save(dst, "PNG", optimize=True)
        else:
            im.save(dst, "WEBP", quality=QUALITY)


def collect_projects(root, out, problems, do_optimize=True):
    pdir = root / "projects"
    site = load_site(root, problems)
    cats = {c.lower(): c for c in site["categories"]}
    projects = []
    if not pdir.is_dir():
        problems.append("The folder 'projects' is missing.")
        return site, projects
    for folder in sorted((p for p in pdir.iterdir() if p.is_dir()), key=lambda p: p.name.lower(), reverse=True):
        if folder.name.startswith(("_", ".")):
            continue
        where = f"projects/{folder.name}"
        info_file = folder / "info.txt"
        info = parse_kv(info_file.read_text(encoding="utf-8"), PROJECT_KEYS) if info_file.exists() else {}
        if first(info, "draft").lower() in ("yes", "true", "1"):
            continue
        if not info_file.exists():
            problems.append(f"{where}: there is no 'info.txt' file inside this folder. Copy it from projects/_TEMPLATE.")
        category = first(info, "category")
        if info_file.exists() and not category:
            problems.append(f"{where}/info.txt: the line 'category:' is missing or empty. Choose one of: {', '.join(site['categories'])}")
        elif category and category.lower() not in cats:
            problems.append(f"{where}/info.txt: category '{category}' is not in the menu. Choose one of: {', '.join(site['categories'])}")

        files = sorted((f for f in folder.iterdir() if f.is_file()), key=lambda f: natural_key(f.name))
        for f in files:
            if f.suffix.lower() in KNOWN_BUT_UNSUPPORTED:
                problems.append(f"{where}/{f.name}: this format is not supported on the web. Please export it as JPG or PNG.")
        imgs = [f for f in files if f.suffix.lower() in IMAGE_EXT]
        cover_src = next((f for f in imgs if f.stem.lower() == "cover"), None)
        gallery_src = [f for f in imgs if f is not cover_src] or ([cover_src] if cover_src else [])
        videos = []
        for v in info.get("video", []):
            if not v:
                continue
            e = video_embed(v)
            if e:
                videos.append({"video": e})
            else:
                problems.append(f"{where}/info.txt: the video link '{v}' is not a YouTube or Vimeo link.")
        if not imgs:
            problems.append(f"{where}: there are no photos in this folder (jpg, png or webp).")
            continue

        slug = slug_name(folder.name)
        base = out / "images" / slug
        used, images = set(), []
        def target(f, prefix=""):
            n = prefix + slug_name(f.stem)
            while n in used:
                n += "-x"
            used.add(n)
            return base / (n + (".png" if f.suffix.lower() == ".png" else ".jpg" if f.suffix.lower() in (".jpg", ".jpeg") else ".webp"))
        try:
            for f in gallery_src:
                dst = target(f)
                if do_optimize:
                    optimize(f, dst, MAX_SIDE)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
                images.append(f"images/{slug}/{dst.name}")
            thumb_src = cover_src or gallery_src[0]
            tdst = base / ("thumb" + (".png" if thumb_src.suffix.lower() == ".png" else ".jpg"))
            if tdst.suffix == ".jpg" and thumb_src.suffix.lower() == ".webp":
                tdst = base / "thumb.webp"
            optimize(thumb_src, tdst, THUMB_SIDE) if do_optimize else (tdst.parent.mkdir(parents=True, exist_ok=True), shutil.copy2(thumb_src, tdst))
        except Exception as e:  # corrupted image etc.
            problems.append(f"{where}: could not read one of the photos ({e}). Try exporting it again as JPG.")
            continue

        year = first(info, "year") or (re.match(r"^(\d{4})", folder.name).group(1) if re.match(r"^\d{4}", folder.name) else "")
        projects.append({
            "slug": slug,
            "title": first(info, "title") or (f"{year} - " if year else "") + re.sub(r"^\d{4}[-_ ]*", "", folder.name).replace("-", " ").replace("_", " ").strip().title(),
            "year": year,
            "category": cats.get(category.lower(), category),
            "cover": f"images/{slug}/{tdst.name}",
            "description": first(info, "description"),
            "images": videos + images,
        })
    return site, projects


def build(root, out=None, do_optimize=True):
    root = Path(root)
    out = Path(out) if out else root / "dist"
    problems = []
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(root / "web", out)
    site, projects = collect_projects(root, out, problems, do_optimize)
    # logo
    if site.get("logo"):
        logo = root / "assets" / site["logo"]
        if logo.exists():
            shutil.copy2(logo, out / ("logo" + logo.suffix.lower()))
            site["logo"] = "logo" + logo.suffix.lower()
        else:
            problems.append(f"site.txt: the logo file 'assets/{site['logo']}' was not found.")
            site["logo"] = ""
    if problems:
        raise BuildError(problems)
    (out / "data").mkdir(exist_ok=True)
    (out / "data" / "projects.json").write_text(json.dumps({"site": site, "projects": projects}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return site, projects


def content_signature(root):
    """A number that changes whenever a project, setting or design file changes."""
    root = Path(root)
    sig = 0
    for sub in ("projects", "web", "assets"):
        for f in (root / sub).rglob("*"):
            if f.is_file():
                st = f.stat()
                sig += int(st.st_mtime_ns % 10**9) + st.st_size
    f = root / "site.txt"
    return sig + (f.stat().st_mtime_ns % 10**9 if f.exists() else 0)


def watch(a):
    last = content_signature(a.root)
    while True:
        time.sleep(1)
        now = content_signature(a.root)
        if now != last:
            last = now
            try:
                _, projects = build(a.root, a.out, not a.no_optimize)
                print(f"Rebuilt: {len(projects)} project(s).")
            except BuildError as e:
                print("\nProblems found (the preview keeps showing the last good version):")
                for p in e.problems:
                    print(f"  - {p}")
            except Exception as e:
                print(f"Rebuild failed: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out")
    ap.add_argument("--no-optimize", action="store_true")
    ap.add_argument("--serve", action="store_true")
    a = ap.parse_args(argv)
    try:
        site, projects = build(a.root, a.out, not a.no_optimize)
    except BuildError as e:
        print("\nThe website could not be built. Please fix these problems:\n")
        for p in e.problems:
            print(f"  - {p}")
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::error title=Website problem::{p}")
        print()
        return 1
    print(f"OK: {len(projects)} project(s) built.")
    if a.serve:
        import functools, http.server
        out = Path(a.out) if a.out else Path(a.root) / "dist"
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        h = functools.partial(Quiet, directory=str(out))
        threading.Thread(target=watch, args=(a, ), daemon=True).start()
        print("Preview on http://localhost:8000  (Ctrl+C to stop)")
        print("The preview rebuilds by itself when you save a file: just refresh the browser.")
        http.server.ThreadingHTTPServer(("", 8000), h).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
