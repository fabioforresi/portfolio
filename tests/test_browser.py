"""Opens the built site in a real browser and clicks through it."""
import json
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


def test_gallery_menu_and_sample_projects(page):
    assert [label.lower() for label in page.locator("nav a").all_inner_texts()] == [
        "gallery", "short", "mid", "long", "afro", "contact"
    ]
    assert page.locator(".card").count() == 4
    assert page.locator(".card img[src$='.svg']").count() == 4
    sizes = page.locator("nav a").evaluate_all(
        "(links) => links.map(link => parseFloat(getComputedStyle(link).fontSize))"
    )
    assert sizes[0] > sizes[1] and sizes[-1] > sizes[1]


def test_contact_form_uses_mailto(page):
    page.goto(page.url.split("#")[0] + "#/contact")
    page.wait_for_selector(".contact-form")
    assert page.locator("#contact-name").is_visible()
    assert page.locator("#contact-email").get_attribute("type") == "email"
    assert page.locator("#contact-message").is_visible()
    assert page.locator("#contact-form").get_attribute("data-recipient") == "fabio.forresi@gmail.com"


def test_overview_images_load(page):
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
    page.goto(site + "#/category/short")
    page.wait_for_selector(".card")
    assert page.locator(".card").count() == 1
    assert page.locator(".card h3").inner_text().lower() == "textured crop with low fade"


def test_project_page_with_future_gallery_data(page, site):
    image = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
    projects = [
        {"slug": "short-cut", "title": "Short cut", "category": "SHORT", "year": "", "description": "", "cover": image, "images": [image]},
        {"slug": "mid-cut", "title": "Mid cut", "category": "MID", "year": "", "description": "", "cover": image, "images": [image]},
    ]
    page.route("**/data/projects.json", lambda route: route.fulfill(
        content_type="application/json",
        body=json.dumps({"site": {"name": "Fabio Forresi", "categories": ["SHORT", "MID", "LONG", "AFRO"]}, "projects": projects}),
    ))
    page.goto(site + "?fixture=projects#/project/short-cut")
    page.wait_for_selector(".project h1")
    assert page.locator(".project h1").inner_text().lower() == "short cut"
    assert page.locator(".media img").count() == 1
    assert page.locator(".related .card").count() == 1


def test_contact_and_no_js_errors(page, site):
    page.goto(site + "#/contact")
    page.wait_for_selector(".contact-form")
    assert page.locator(".contact-form [required]").count() == 3
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
        pg.click("nav a:has-text('afro')")
        pg.wait_for_selector(".card")
        pg.locator("nav a").first.wait_for(state="hidden")
        assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth")
    finally:
        pg.close()
