# Portfolio website

Static portfolio site published with GitHub Pages. Content lives in plain folders and text files,
so projects can be added by drag-and-drop without touching code.

**Non-technical guide → [EDITING.md](EDITING.md)**

## How it works
```
projects/<year-name>/   photos + info.txt  (one folder per project)
site.txt                name, menu categories, contact
assets/                 optional logo
web/                    HTML / CSS / JS of the site (the design)
scripts/build.py        reads the folders, resizes photos, writes dist/ + data/projects.json
tests/                  unit tests + real-browser tests (pytest, Playwright)
.github/workflows/      ci.yml (checks on branches/PRs) and deploy.yml (test → build → publish)
```
On every push to `main`, GitHub Actions runs the tests, builds `dist/` and deploys it to Pages.
Content mistakes (missing category, unsupported photo format…) fail the build with a plain-language message
and the live site stays untouched.

## Local development
```bash
pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/build.py --serve     # preview on http://localhost:8000 (rebuilds on save)
# in VS Code: Ctrl+Shift+B
python -m pytest                    # tests
```

## Design changes
The look is a dark theme matched to the original Adobe Portfolio site (condensed caps menu, 16:9 covers with hover title + year, full-screen mobile menu, "You may also like").
Colours, fonts, number of columns, gaps and cover shape: variables in the `THEME SETTINGS` block at the top of `web/css/style.css`. Fonts (Bebas Neue, Montserrat, SIL OFL) are self-hosted in `web/fonts`. Layout and routing: `web/js/main.js`.
Source images are never modified; optimized copies are generated into `dist/` (ignored by git).

## Setup
Settings → Pages → Source: **GitHub Actions**.
