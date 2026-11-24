"""Opens the built site in a real browser and clicks through it."""
import functools
import http.server
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

import build as B

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    B.build(REPO, out)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def page(site):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.errors = errors
        pg.goto(site)
        pg.wait_for_selector(".card")
        yield pg
        b.close()


def test_overview_menu_and_images_load(page):
    assert page.locator("nav a").count() >= 7  # Overview + categories + Contact
    assert page.locator(".card").count() >= 10
    broken = page.evaluate("""async () => {
      const images = [...document.querySelectorAll(".card img")];
      await Promise.all(images.map(img => {
        img.loading = "eager";
        if (img.complete) return;
        return new Promise(resolve => {
          img.addEventListener("load", resolve, { once: true });
          img.addEventListener("error", resolve, { once: true });
        });
      }));
      return images.filter(img => img.naturalWidth === 0).length;
    }""")
    assert broken == 0


def test_ludwig_desktop_layout(page, site):
    page.goto(site)
    layout = page.evaluate("""() => {
      const grid = document.querySelector(".grid");
      const card = document.querySelector(".card");
      const header = document.querySelector(".site-header");
      const nav = document.querySelector("nav");
      const logo = document.querySelector(".logo");
      return {
        columns: getComputedStyle(grid).gridTemplateColumns.split(" ").length,
        aspectRatio: card.getBoundingClientRect().width / card.getBoundingClientRect().height,
        sideMargin: grid.getBoundingClientRect().left,
        headerPosition: getComputedStyle(header).position,
        navRight: nav.getBoundingClientRect().right,
        logoLeft: logo.getBoundingClientRect().left
      };
    }""")
    assert layout["columns"] == 2
    assert abs(layout["aspectRatio"] - 16 / 9) < 0.02
    assert layout["sideMargin"] > 0
    assert layout["headerPosition"] == "sticky"
    assert layout["navRight"] < layout["logoLeft"]


def test_category_filter(page, site):
    page.goto(site + "#/category/landscape")
    page.wait_for_selector(".card")
    titles = page.locator(".card h3").all_inner_texts()  # hidden until hover, still in the page
    assert titles and len(titles) == 3


def test_project_page_and_video(page, site):
    page.goto(site + "#/project/2025-neon-nights")
    page.wait_for_selector(".project h1")
    assert "neon nights" in page.locator(".project h1").inner_text().lower()
    assert page.locator(".video iframe").count() == 1
    assert page.locator(".project img").count() >= 1
    assert page.locator(".related .card").count() >= 1  # "You may also like"


def test_contact_and_no_js_errors(page, site):
    page.goto(site + "#/contact")
    page.wait_for_selector(".contact")
    assert page.locator(".contact a[href^='mailto:']").count() == 1
    external = [e for e in page.errors if "vimeo" not in e.lower() and "ERR_" not in e]
    assert external == []


def test_mobile_menu_opens_and_closes(page, site):
    browser = page.context.browser
    pg = browser.new_page(viewport={"width": 390, "height": 800})
    try:
        pg.goto(site)
        pg.wait_for_selector(".card")
        layout = pg.evaluate("""() => ({
          columns: getComputedStyle(document.querySelector(".grid")).gridTemplateColumns.split(" ").length,
          scrollWidth: document.documentElement.scrollWidth,
          viewportWidth: innerWidth
        })""")
        assert layout["columns"] == 1
        assert layout["scrollWidth"] == layout["viewportWidth"]
        assert pg.locator("#burger").is_visible()
        assert not pg.locator("nav a").first.is_visible()

        pg.click("#burger")
        pg.wait_for_selector("nav a", state="visible")
        assert pg.locator("#burger").get_attribute("aria-expanded") == "true"
        assert pg.evaluate("document.body.classList.contains('menu-open')")
        pg.keyboard.press("Escape")
        pg.locator("nav a").first.wait_for(state="hidden")
        assert pg.locator("#burger").get_attribute("aria-expanded") == "false"
        assert not pg.evaluate("document.body.classList.contains('menu-open')")

        pg.click("#burger")
        pg.wait_for_selector("nav a", state="visible")
        pg.click("nav a:has-text('Street')")
        pg.wait_for_selector(".card")
        pg.locator("nav a").first.wait_for(state="hidden")
        assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth")
    finally:
        pg.close()
