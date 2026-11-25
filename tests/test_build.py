import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

import build as B

REPO = Path(__file__).resolve().parent.parent


def img(path, size=(800, 600)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (120, 130, 140)).save(path)


@pytest.fixture
def root(tmp_path):
    shutil.copytree(REPO / "web", tmp_path / "web")
    (tmp_path / "site.txt").write_text("name: Test\ncategories: Retouching, Video\nlink: IG | https://ig.com/x\n", encoding="utf-8")
    return tmp_path


def project(root, name, info, images=("cover.jpg", "01.jpg")):
    d = root / "projects" / name
    d.mkdir(parents=True, exist_ok=True)
    if info is not None:
        (d / "info.txt").write_text(info, encoding="utf-8")
    for i in images:
        img(d / i)


def test_parse_multiline_and_comments():
    d = B.parse_kv("# c\ntitle: A\ndescription: line1\nline2\nvideo: x\nvideo: y\n", B.PROJECT_KEYS)
    assert d["description"] == ["line1\nline2"] and d["video"] == ["x", "y"]


@pytest.mark.parametrize("url,expected", [
    ("https://vimeo.com/123456", "https://player.vimeo.com/video/123456"),
    ("https://www.youtube.com/watch?v=abc123", "https://www.youtube.com/embed/abc123"),
    ("https://youtu.be/abc123", "https://www.youtube.com/embed/abc123"),
    ("https://example.com/v", None),
])
def test_video_embed(url, expected):
    assert B.video_embed(url) == expected


def test_builds_sorted_newest_first_with_cover(root):
    project(root, "2023-old", "title: Old\ncategory: video\n")
    project(root, "2025-new", "title: New\ncategory: Retouching\nvideo: https://vimeo.com/1\n")
    _, ps = B.build(root)
    assert [p["slug"] for p in ps] == ["2025-new", "2023-old"]
    assert ps[0]["category"] == "Retouching" and ps[1]["category"] == "Video"  # case-insensitive match
    assert ps[0]["cover"].endswith("thumb.jpg") and ps[0]["images"][0] == {"video": "https://player.vimeo.com/video/1"}
    assert ps[0]["images"][1:] == ["images/2025-new/01.jpg"]  # cover.jpg is not repeated in the gallery
    assert (root / "dist" / "data" / "projects.json").exists()


def test_template_and_draft_are_skipped(root):
    project(root, "_TEMPLATE", "title: T\ncategory: Video\n")
    project(root, "2025-wip", "title: W\ncategory: Video\ndraft: yes\n")
    project(root, "2025-ok", "title: OK\ncategory: Video\n")
    _, ps = B.build(root)
    assert [p["slug"] for p in ps] == ["2025-ok"]


def test_single_image_is_both_cover_and_gallery(root):
    project(root, "2025-x", "title: X\ncategory: Video\n", images=("only.jpg",))
    _, ps = B.build(root)
    assert ps[0]["images"] == ["images/2025-x/only.jpg"] and ps[0]["cover"].endswith("thumb.jpg")


def test_svg_placeholders_are_copied_and_published(root):
    d = root / "projects" / "2026-short-cut"
    d.mkdir(parents=True)
    (d / "info.txt").write_text("title: Textured Crop\ncategory: Retouching\n")
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 9"><text>Placeholder</text></svg>'
    (d / "cover.svg").write_text(svg, encoding="utf-8")
    _, ps = B.build(root)
    assert ps[0]["cover"] == "images/2026-short-cut/thumb.svg"
    assert ps[0]["images"] == ["images/2026-short-cut/cover.svg"]
    assert (root / "dist" / ps[0]["cover"]).read_text(encoding="utf-8") == svg


def test_large_images_are_shrunk_and_names_cleaned(root):
    project(root, "2025-big", "title: B\ncategory: Video\n", images=("My Image (1).JPG",))
    _, ps = B.build(root)
    out = root / "dist" / ps[0]["images"][0]
    assert out.name == "my-image-1.jpg"
    img(root / "projects" / "2025-big" / "huge.jpg", (6000, 4000))
    _, ps = B.build(root)
    huge = root / "dist" / "images" / "2025-big" / "huge.jpg"
    assert max(Image.open(huge).size) == B.MAX_SIDE


def test_title_and_year_fall_back_to_folder_name(root):
    project(root, "2024-cool-shoot", "category: Video\n")
    _, ps = B.build(root)
    assert ps[0]["title"] == "2024 - Cool Shoot" and ps[0]["year"] == "2024"


@pytest.mark.parametrize("info,fragment", [
    (None, "no 'info.txt'"),
    ("title: A\n", "'category:' is missing"),
    ("title: A\ncategory: Cooking\n", "not in the menu"),
    ("title: A\ncategory: Video\nvideo: https://example.com/x\n", "not a YouTube or Vimeo"),
])
def test_friendly_errors(root, info, fragment):
    project(root, "2025-bad", info)
    with pytest.raises(B.BuildError) as e:
        B.build(root)
    assert any(fragment in p for p in e.value.problems)


def test_errors_for_no_images_and_unsupported_format(root):
    project(root, "2025-empty", "title: A\ncategory: Video\n", images=())
    d = root / "projects" / "2025-heic"
    d.mkdir()
    (d / "info.txt").write_text("title: H\ncategory: Video\n")
    (d / "unsupported.gif").write_bytes(b"x")
    with pytest.raises(B.BuildError) as e:
        B.build(root)
    text = "\n".join(e.value.problems)
    assert "no images" in text and "JPG, PNG, WebP or SVG" in text


def test_corrupt_image_reports_instead_of_crashing(root):
    project(root, "2025-c", "title: A\ncategory: Video\n", images=())
    (root / "projects" / "2025-c" / "broken.jpg").write_bytes(b"not an image")
    with pytest.raises(B.BuildError) as e:
        B.build(root)
    assert "could not read" in e.value.problems[0]


def test_real_repository_builds(tmp_path):
    _, ps = B.build(REPO, tmp_path / "out")
    assert len(ps) == 4
    assert {p["category"] for p in ps} == {"SHORT", "MID", "LONG", "AFRO"}
    data = json.loads((tmp_path / "out" / "data" / "projects.json").read_text())
    assert data["site"]["categories"] == ["SHORT", "MID", "LONG", "AFRO"]
    assert data["site"]["contact"]["email"] == "fabio.forresi@gmail.com"
    for p in data["projects"]:
        for m in p["images"]:
            if isinstance(m, str):
                assert (tmp_path / "out" / m).exists()
