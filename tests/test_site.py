"""Tests for tools/build_site.py."""

import base64
import gzip
import html
import json
import os
import random
import re
import urllib.parse
import zipfile

import pytest

from tools.build_site import PLACEHOLDERS, REPO_URL, TEMPLATE, ZIP_DATE, build_site, fmt_bytes

MANIFEST = {
    "groups": [
        {"name": "Angled base", "items": [
            {"file": "frederick-base-solid.stl", "label": "Solid", "material": "PLA/PETG",
             "hint": "deck up", "size_mm": [103.0, 190.0, 37.4], "volume_cm3": 80.5, "triangles": 1200},
        ]},
        {"name": "Single-dose hopper", "items": [
            {"file": "frederick-hopper-insert-friction.stl", "label": "Insert: friction", "material": "PLA/PETG",
             "hint": "spout down", "size_mm": [70.0, 70.0, 70.0], "volume_cm3": 23.5, "triangles": 800},
            {"file": "frederick-hopper-insert-screw.stl", "label": "Insert: screw", "material": "PLA/PETG",
             "hint": "spout down", "size_mm": [70.0, 70.0, 70.0], "volume_cm3": 24.4, "triangles": 850,
             "material_note": "PETG or ASA & not PLA: it creeps under the screw clamp"},
            {"file": "frederick-hopper-bellows-open.stl", "label": "Open bellows", "material": "TPU 95A",
             "hint": "ring on the bed </script>", "size_mm": [70.0, 70.0, 62.1], "volume_cm3": 20.0,
             "triangles": 900},
            {"file": "frederick-hopper-2p-body.stl", "label": "Two-piece body", "material": "TPU 95A",
             "hint": "spout down", "size_mm": [70.0, 70.0, 111.3], "volume_cm3": 35.8, "triangles": 1000},
            {"file": "frederick-hopper-cap.stl", "label": "Cap", "material": "PLA/PETG",
             "hint": "top face down", "size_mm": [73.0, 73.0, 8.0], "volume_cm3": 14.6, "triangles": 100},
        ]},
    ],
    "parameters": [["Base angle", "10°"], ["Throat ID", "33.8 mm"]],
    "ghost": {"file": "frederick-grinder-ghost.stl", "placement": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]},
    "bases": {"solid": "frederick-base-solid.stl"},
    # the cap is shared by two kits: it must still be one download and one embedded mesh
    "kits": [
        {"key": "3-part", "inserts": {"friction": "frederick-hopper-insert-friction.stl",
                                      "screw": "frederick-hopper-insert-screw.stl"},
         "files": ["frederick-hopper-bellows-open.stl", "frederick-hopper-cap.stl"], "placements": {}},
        {"key": "two-piece", "inserts": {}, "files": ["frederick-hopper-2p-body.stl", "frederick-hopper-cap.stl"],
         "placements": {}},
    ],
    "default": {"base": "solid", "kit": "3-part", "insert": "friction"},
}
GHOST = MANIFEST["ghost"]["file"]
FILES = ["frederick-base-solid.stl", "frederick-hopper-insert-friction.stl", "frederick-hopper-insert-screw.stl",
         "frederick-hopper-bellows-open.stl", "frederick-hopper-2p-body.stl", "frederick-hopper-cap.stl"]
# zip name -> its STLs: one per base variant, per kit and insert variant, and everything
BUNDLES = {
    "frederick-base-solid.zip": ["frederick-base-solid.stl"],
    "frederick-hopper-3-part-friction.zip": ["frederick-hopper-insert-friction.stl",
                                             "frederick-hopper-bellows-open.stl", "frederick-hopper-cap.stl"],
    "frederick-hopper-3-part-screw.zip": ["frederick-hopper-insert-screw.stl",
                                          "frederick-hopper-bellows-open.stl", "frederick-hopper-cap.stl"],
    "frederick-hopper-two-piece.zip": ["frederick-hopper-2p-body.stl", "frederick-hopper-cap.stl"],
    "frederick-all.zip": FILES,
}


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
    (tmp_path / "build" / GHOST).write_bytes(random.Random(9).randbytes(3000))
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
    assert sorted(blocks) == sorted(f.removesuffix(".stl") for f in FILES + [GHOST])
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


def section(page, start, end):
    """Cut the page between two element ids.

    Args:
        page: Generated page.
        start: id the section starts at.
        end: id of the next section.

    Returns:
        str, the page between the two.
    """
    return page.split(f'id="{start}"', 1)[1].split(f'id="{end}"', 1)[0]


def local_links(html):
    """Relative stl/ and bundles/ links with whether their <a> has the download attribute.

    Args:
        html: Page or part of it.

    Returns:
        List of (unquoted href, has download attribute).
    """
    return [(urllib.parse.unquote(href), " download" in tag)
            for tag, href in re.findall(r'(<a [^>]*href="((?:stl|bundles)/[^"]+)"[^>]*>)', html)]


def test_download_links_point_at_copied_files(root, page):
    """Every stl/ and bundles/ link is relative, has `download` and resolves in _site; the full list has each STL once.

    Args:
        root: Fake repo root fixture.
        page: Generated page fixture.
    """
    links = local_links(page)
    assert links and all(download for _, download in links)
    for href, _ in links:
        assert (root / "_site" / href).is_file(), href
    stl_hrefs = [h for h, _ in local_links(section(page, "downloads", "parameters")) if h.startswith("stl/")]
    assert sorted(stl_hrefs) == sorted(f"stl/{f}" for f in FILES)   # once each
    assert {h for h, _ in links if h.startswith("bundles/")} == {f"bundles/{b}" for b in BUNDLES}
    assert not (root / "_site" / "stl" / "stale-unlisted.stl").exists()
    assert (root / "_site" / ".nojekyll").is_file()


def test_bundles_exist(root, page):
    """_site/bundles/ has one zip per base variant, per kit and insert variant, and one with everything.

    Args:
        root: Fake repo root fixture.
        page: Generated page fixture.
    """
    assert sorted(os.listdir(root / "_site" / "bundles")) == sorted(BUNDLES)


@pytest.mark.parametrize("name", BUNDLES)
def test_bundle_members(root, page, name):
    """Each zip holds exactly its STLs (byte-exact) plus README.txt, sorted, stamped ZIP_DATE.

    Args:
        root: Fake repo root fixture.
        page: Generated page fixture.
        name: Zip file name.
    """
    items = {it["file"]: it for g in MANIFEST["groups"] for it in g["items"]}
    with zipfile.ZipFile(root / "_site" / "bundles" / name) as zf:
        assert zf.namelist() == sorted(BUNDLES[name] + ["README.txt"])
        assert all(info.date_time == ZIP_DATE for info in zf.infolist())
        for f in BUNDLES[name]:
            assert zf.read(f) == (root / "stl" / f).read_bytes()
        readme = zf.read("README.txt").decode("utf-8")
    assert REPO_URL in readme and f"{REPO_URL}/blob/main/config.py" in readme
    for f in BUNDLES[name]:
        assert f in readme and items[f]["material"] in readme and items[f]["hint"] in readme
        if "material_note" in items[f]:   # optional: only the items that carry one
            assert f"Note:     {items[f]['material_note']}" in readme


def test_bundles_deterministic(root):
    """Two builds give byte-identical zips, even when the STLs' timestamps change in between.

    Args:
        root: Fake repo root fixture.
    """
    build_site(root, root / "a")
    for f in FILES:
        os.utime(root / "stl" / f, (1_700_000_000, 1_700_000_000))
    build_site(root, root / "b")
    for name in BUNDLES:
        assert (root / "a" / "bundles" / name).read_bytes() == (root / "b" / "bundles" / name).read_bytes()


def test_print_panel(page):
    """One "Print these" set per base variant and per kit and insert: its STLs, their print info and its zip.

    Only the default base's set starts visible; the page script switches them.

    Args:
        page: Generated page fixture.
    """
    items = {it["file"]: it for g in MANIFEST["groups"] for it in g["items"]}
    sets = re.findall(r'<div class="print-set" ([^>]*)>(.*?)</ul></div>', section(page, "print", "downloads"), re.S)
    assert len(sets) == len(BUNDLES) - 1
    shown = [attrs for attrs, _ in sets if " hidden" not in attrs]
    assert shown == ['data-base="solid" data-title="Solid base"']
    for attrs, body in sets:
        hrefs = [h for h, _ in local_links(body)]
        zips = [h for h in hrefs if h.startswith("bundles/")]
        assert len(zips) == 1 and "Download bundle (.zip)" in body
        assert [h for h in hrefs if h.startswith("stl/")] == [f"stl/{f}" for f in BUNDLES[zips[0][8:]]]
        for f in BUNDLES[zips[0][8:]]:
            assert items[f]["material"] in body
        notes = re.findall(r'<span class="dl-note">([^<]*)</span>', body)
        assert notes == [html.escape(items[f]["material_note"]) for f in BUNDLES[zips[0][8:]]
                         if "material_note" in items[f]]
    assert 'data-kit="3-part" data-insert="screw"' in page and 'data-kit="two-piece" data-insert=""' in page


def test_github_links(page):
    """The repo link, the config.py link and a GitHub link per STL are on the page.

    Args:
        page: Generated page fixture.
    """
    assert f'href="{REPO_URL}"' in page and 'class="gh-mark"' in page
    assert f'href="{REPO_URL}/blob/main/config.py"' in page
    for f in FILES:
        assert f'href="{REPO_URL}/blob/main/stl/{f}"' in section(page, "downloads", "parameters")


def test_accessibility_basics(page):
    """Toggles are buttons with aria-pressed or role=switch checkboxes, focus is visible, downloads are labelled.

    Args:
        page: Generated page fixture.
    """
    assert re.search(r'<button type="button" data-view="hero" aria-pressed="true">', page)
    assert 'b.setAttribute("aria-pressed"' in page and ":focus-visible" in page
    assert '<input type="checkbox" id="autorotate" role="switch">' in page
    assert 'canvas.setAttribute("aria-label"' in page
    for tag in re.findall(r'<a class="dl-get" [^>]*>', page):
        assert "aria-label=" in tag or 'href="#print"' in tag


@pytest.mark.parametrize(("n", "text"), [(90, "90 B"), (31_400, "31 kB"), (1_260_000, "1.3 MB")])
def test_fmt_bytes(n, text):
    """Byte counts read as B, kB or MB.

    Args:
        n: Size in bytes.
        text: Expected label.
    """
    assert fmt_bytes(n) == text


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


def test_ghost_embedded_not_downloadable(root, page):
    """The ghost is embedded byte-exact from build/, but never linked, bundled or copied to _site/stl/.

    Args:
        root: Fake repo root fixture.
        page: Generated page fixture.
    """
    stem = GHOST.removesuffix(".stl")
    block = re.search(rf'<script type="application/octet-stream" id="mesh-{stem}">([^<]*)</script>', page)
    assert gzip.decompress(base64.b64decode(block.group(1), validate=True)) == (root / "build" / GHOST).read_bytes()
    assert stem not in "".join(re.findall(r'href="([^"]*)"', page))
    assert not (root / "_site" / "stl" / GHOST).exists()
    with zipfile.ZipFile(root / "_site" / "bundles" / "frederick-all.zip") as zf:
        assert GHOST not in zf.namelist()


def test_show_on_grinder_ui(page):
    """The toggle starts off, the approximation note and the final-form caption are there, matrices are read
    row-major, and the upright-only view is gone.

    Args:
        page: Generated page fixture.
    """
    assert re.search(r'<input type="checkbox" id="on-grinder" role="switch">\s*Show on grinder', page)
    assert "Approximate grinder for context — not a measured model." in page
    assert '<p id="final-caption" hidden></p>' in page and '"Final form: "' in page
    assert "manifest.kits" in page and "upright" not in page and "partners" not in page
    assert "new THREE.Matrix4().set(...m)" in page and ".fromArray(" not in page.split("<script type=\"module\">")[1]
    assert "depthWrite: false" in page


def test_missing_ghost_fails(root):
    """A manifest whose ghost STL is missing from build/ is rejected.

    Args:
        root: Fake repo root fixture.
    """
    (root / "build" / GHOST).unlink()
    with pytest.raises(SystemExit, match=GHOST):
        build_site(root, root / "_site")
