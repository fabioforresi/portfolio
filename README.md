# Fabio Forresi — Barbiere

Static barbershop portfolio published with GitHub Pages. Gallery sections and contact settings live
in plain text files; project images can be added by drag-and-drop without touching code.

**Non-technical guide → [EDITING.md](EDITING.md)**

## How it works
```
projects/<year-name>/   project images + info.txt  (one folder per haircut)
site.txt                name, menu categories, contact
assets/                 optional logo
web/                    HTML / CSS / JS of the site (the design)
scripts/build.py        reads the folders, optimizes images, writes dist/ + data/projects.json
tests/                  unit tests + real-browser tests (pytest, Playwright)
.github/workflows/      ci.yml (checks on branches/PRs) and deploy.yml (test → build → publish)
```
On every push to `main`, GitHub Actions runs the tests, builds `dist/` and deploys it to Pages.
Content mistakes (missing category, unsupported image format…) fail the build with a plain-language message
and the live site stays untouched.

## Local development
```bash
uv sync
uv run python -m playwright install chromium
uv run python scripts/build.py --serve  # preview on http://localhost:8000 (rebuilds on save)
# in VS Code: Ctrl+Shift+B
uv run pytest -q                    # tests
```

## Design changes
The look is inspired by Adobe Portfolio's Ludwig theme: centered logo, horizontal desktop navigation, dark background, two-column 16:9 cover grid with hover titles, and a full-screen mobile menu. Colours, fonts, columns, spacing and cover shape are set at the top of `web/css/style.css`. Bebas Neue is self-hosted in `web/fonts`; layout and routing are in `web/js/main.js`.
The four sample haircuts use SVG placeholder covers; replace them with your own images when ready. Source images are never modified; optimized copies are generated into `dist/` (ignored by git).

## Setup
Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once, then run `uv sync` in the project folder. Settings → Pages → Source: **GitHub Actions**.
