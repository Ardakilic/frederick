"""Tests for tools/build_site.py."""

import base64
import gzip
import json
import random
import re
import urllib.parse

import pytest

from tools.build_site import TEMPLATE, build_site

MANIFEST = {
    "groups": [
        {"name": "Angled base", "items": [
            {"file": "frederick-base-solid.stl", "label": "Solid", "material": "PLA/PETG",
             "hint": "deck up", "size_mm": [103.0, 190.0, 37.4], "volume_cm3": 80.5, "triangles": 1200},
        ]},
        {"name": "Single-dose hopper", "items": [
            {"file": "frederick-hopper-bellows.stl", "label": "Bellows", "material": "TPU 95A",
             "hint": "cap on the bed </script>", "size_mm": [70.0, 70.0, 58.0], "volume_cm3": 20.0,
             "triangles": 900},
        ]},
    ],
    "parameters": [["Base angle", "10°"], ["Throat ID", "33.8 mm"]],
}
FILES = ["frederick-base-solid.stl", "frederick-hopper-bellows.stl"]
PLACEHOLDERS = ("@MANIFEST@", "@DOWNLOADS@", "@PARAMETERS@", "@MESHES@")


@pytest.fixture
def root(tmp_path):
    """A fake repo root with build/manifest.json and binary-looking dummy STLs.

    Each STL is random bytes (every byte value occurs), different per file, so
    the gzip + base64 round trip is checked on real binary data.

    Args:
        tmp_path: pytest temporary directory.

    Returns:
        pathlib.Path of the fake root.
    """
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    (tmp_path / "stl").mkdir()
    for i, f in enumerate(FILES):
        (tmp_path / "stl" / f).write_bytes(random.Random(i).randbytes(5000 + i))
    (tmp_path / "stl" / "stale-unlisted.stl").write_bytes(b"old")
    return tmp_path


@pytest.fixture
def page(root):
    """Build the site from the fake root and return index.html's text.

    Args:
        root: Fake repo root fixture.

    Returns:
        str, the generated page.
    """
    build_site(root, root / "_site")
    return (root / "_site" / "index.html").read_text(encoding="utf-8")


def test_every_stl_embedded_byte_exact(root, page):
    """Each STL has one mesh block, and base64 -> gunzip gives its exact bytes.

    Args:
        root: Fake repo root fixture.
        page: Generated page fixture.
    """
    blocks = dict(re.findall(r'<script type="application/octet-stream" id="mesh-([^"]+)">([^<]*)</script>', page))
    assert sorted(blocks) == sorted(f.removesuffix(".stl") for f in FILES)
    for f in FILES:
        decoded = gzip.decompress(base64.b64decode(blocks[f.removesuffix(".stl")], validate=True))
        assert decoded == (root / "stl" / f).read_bytes()


def test_no_stl_fetch(page):
    """The page decodes the embedded STLs and never fetches them (file:// blocks fetch).

    Args:
        page: Generated page fixture.
    """
    assert "fetch(" not in page
    assert "loadAsync" not in page
    assert "loader.parse(" in page and 'DecompressionStream("gzip")' in page


def test_download_links_point_at_copied_files(root, page):
    """Every STL has a plain relative download link to a file in _site/stl/.

    Args:
        root: Fake repo root fixture.
        page: Generated page fixture.
    """
    hrefs = re.findall(r'<a href="(stl/[^"]+)" download>', page)
    assert sorted(urllib.parse.unquote(h) for h in hrefs) == sorted(f"stl/{f}" for f in FILES)
    for h in hrefs:
        assert (root / "_site" / urllib.parse.unquote(h)).is_file()
    assert not (root / "_site" / "stl" / "stale-unlisted.stl").exists()
    assert (root / "_site" / ".nojekyll").is_file()


def test_placeholders_filled(page):
    """No at-sign placeholder is left; the manifest JSON cannot close its script tag.

    Args:
        page: Generated page fixture.
    """
    assert re.search(r"@[A-Z]+@", page) is None
    assert "Throat ID" in page and "33.8 mm" in page
    assert "</script>\"" not in page


@pytest.mark.parametrize("key", PLACEHOLDERS)
def test_missing_placeholder_fails(root, tmp_path, key):
    """A template without one of the placeholders is rejected.

    Args:
        root: Fake repo root fixture.
        tmp_path: pytest temporary directory.
        key: Placeholder removed from the template.
    """
    bad = tmp_path / "bad.html"
    bad.write_text(open(TEMPLATE, encoding="utf-8").read().replace(key, ""), encoding="utf-8")
    with pytest.raises(SystemExit, match=key):
        build_site(root, root / "_site", template=bad)


def test_missing_stl_fails(root):
    """A manifest entry without its STL is rejected.

    Args:
        root: Fake repo root fixture.
    """
    (root / "stl" / FILES[0]).unlink()
    with pytest.raises(SystemExit, match=FILES[0]):
        build_site(root, root / "_site")
