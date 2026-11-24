"""Assemble _site/ for GitHub Pages from build/manifest.json and stl/.

    python3 tools/build_site.py

Writes _site/index.html (preview/template.html with the manifest filled in),
copies every STL the manifest lists to _site/stl/, and adds _site/.nojekyll.
Run `python3 generate.py` first. Standard library only.

The page is self-contained: every STL is embedded as gzip + base64 of its exact
bytes, and the browser decodes it with DecompressionStream, so index.html
works when opened straight from disk (file://, where fetch() is blocked).
Only three.js comes from the network (jsDelivr, which sends CORS headers).
The download links stay plain relative stl/<file> hrefs.
"""

import base64
import gzip
import html
import json
import os
import shutil
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "preview", "template.html")


def downloads_html(manifest):
    """Render the download list: one link per STL with its print info.

    Args:
        manifest: Manifest dict written by generate.py.

    Returns:
        HTML string.
    """
    out = []
    for group in manifest["groups"]:
        out.append(f"<h3>{html.escape(group['name'])}</h3>\n<ul class=\"downloads\">")
        for it in group["items"]:
            size = " × ".join(f"{v:g}" for v in it["size_mm"])
            out.append(
                f"<li><a href=\"stl/{urllib.parse.quote(it['file'])}\" download>{html.escape(it['label'])}</a>"
                f" <code>{html.escape(it['file'])}</code>"
                f"<span>{html.escape(it['material'])}: {html.escape(it['hint'])}</span>"
                f"<span class=\"meta\">{size} mm · {it['volume_cm3']:g} cm³ · {it['triangles']} triangles</span></li>")
        out.append("</ul>")
    return "\n".join(out)


def parameters_html(manifest):
    """Render the parameter table rows.

    Args:
        manifest: Manifest dict written by generate.py.

    Returns:
        HTML string of <tr> rows.
    """
    return "\n".join(f"<tr><th scope=\"row\">{html.escape(name)}</th><td>{html.escape(value)}</td></tr>"
                     for name, value in manifest["parameters"])


def meshes_html(stl_dir, files):
    """Embed each STL as a gzip + base64 data block the page decodes itself.

    Args:
        stl_dir: Folder holding the STL files.
        files: STL file names, in manifest order.

    Returns:
        HTML string: one <script type="application/octet-stream"
        id="mesh-<file without .stl>"> element per file. Base64 has no "<",
        so the payload cannot end its element early.
    """
    out = []
    for f in files:
        with open(os.path.join(stl_dir, f), "rb") as fh:
            blob = gzip.compress(fh.read(), 9, mtime=0)   # mtime=0: same bytes in, same page out
        slug = html.escape(os.path.splitext(f)[0])
        out.append(f'<script type="application/octet-stream" id="mesh-{slug}">'
                   f'{base64.b64encode(blob).decode("ascii")}</script>')
    return "\n".join(out)


def build_site(root, out_dir, template=TEMPLATE):
    """Write index.html, the listed STLs and .nojekyll into out_dir.

    Args:
        root: Folder holding build/manifest.json and stl/.
        out_dir: Site folder; deleted and recreated.
        template: Page template with @MANIFEST@, @DOWNLOADS@, @PARAMETERS@ and
            @MESHES@.

    Raises:
        SystemExit: The manifest, a listed STL or a template placeholder is missing.
    """
    manifest_path = os.path.join(root, "build", "manifest.json")
    if not os.path.exists(manifest_path):
        raise SystemExit(f"{manifest_path} not found - run generate.py (make generate) first")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(template, encoding="utf-8") as f:
        page = f.read()
    files = [it["file"] for g in manifest["groups"] for it in g["items"]]
    missing = [f for f in files if not os.path.exists(os.path.join(root, "stl", f))]
    if missing:
        raise SystemExit(f"STLs listed in the manifest are missing from stl/: {', '.join(missing)}")
    fills = {
        # inside <script type="application/json">: only "</" could end the element early
        "@MANIFEST@": json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/"),
        "@DOWNLOADS@": downloads_html(manifest),
        "@PARAMETERS@": parameters_html(manifest),
        "@MESHES@": meshes_html(os.path.join(root, "stl"), files),
    }
    for key, value in fills.items():
        if key not in page:
            raise SystemExit(f"{template} has no {key} placeholder")
        page = page.replace(key, value)

    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(os.path.join(out_dir, "stl"))
    for f in files:
        shutil.copy2(os.path.join(root, "stl", f), os.path.join(out_dir, "stl", f))
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()


if __name__ == "__main__":
    build_site(ROOT, os.path.join(ROOT, "_site"))
    size = os.path.getsize(os.path.join(ROOT, "_site", "index.html"))
    print(f"_site/index.html ({size / 1e6:.2f} MB, opens from disk; no server needed)")
