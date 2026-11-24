"""Assemble _site/ for GitHub Pages from build/manifest.json and stl/.

    python3 tools/build_site.py

Writes _site/index.html (preview/template.html with the manifest filled in),
copies every STL the manifest lists to _site/stl/, writes the zip bundles to
_site/bundles/ (one per base variant, one per hopper kit and insert variant,
one with everything; each with a README.txt) and adds _site/.nojekyll. Run
`python3 generate.py` first. Standard library only.

The page is self-contained: every STL is embedded as gzip + base64 of its exact
bytes, and the browser decodes it with DecompressionStream, so index.html
works when opened straight from disk (file://, where fetch() is blocked).
Only three.js comes from the network (jsDelivr, which sends CORS headers).
The download links stay plain relative stl/<file> and bundles/<zip> hrefs.
The grinder ghost (build/<manifest ghost file>) is embedded the same way for
the "Show on grinder" view, but never copied to _site/stl/, bundled or linked.
"""

import base64
import gzip
import html
import json
import os
import shutil
import urllib.parse
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "preview", "template.html")
REPO_URL = "https://github.com/Ardakilic/frederick"
ZIP_DATE = (1980, 1, 1, 0, 0, 0)  # every zip entry's timestamp: rebuilds are byte-identical
PLACEHOLDERS = ("@MANIFEST@", "@DOWNLOADS@", "@PRINT@", "@PARAMETERS@", "@MESHES@", "@REPO@")


def fmt_bytes(n):
    """Format a byte count for the page.

    Args:
        n: Size in bytes.

    Returns:
        String such as "1.2 MB", "310 kB" or "90 B".
    """
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} kB" if n >= 1e3 else f"{n} B"


def github_url(file):
    """Link to a committed STL on GitHub (which renders STLs in 3D).

    Args:
        file: STL file name inside stl/.

    Returns:
        URL string.
    """
    return f"{REPO_URL}/blob/main/stl/{urllib.parse.quote(file)}"


def bundles(manifest):
    """List the zip bundles: one per base variant, one per hopper kit and insert variant, one with everything.

    Args:
        manifest: Manifest dict written by generate.py.

    Returns:
        List of dicts with name (zip file name), title, files (STL names, bottom up for a kit)
        and slot ({"base": variant}, {"kit": key, "insert": variant or ""}, or {} for everything).
    """
    labels = {it["file"]: it["label"] for g in manifest["groups"] for it in g["items"]}
    out = [{"name": f"frederick-base-{variant}.zip", "title": f"{labels[file]} base", "files": [file],
            "slot": {"base": variant}} for variant, file in manifest["bases"].items()]
    for kit in manifest["kits"]:
        for insert, file in list(kit["inserts"].items()) or [("", None)]:
            out.append({"name": f"frederick-hopper-{kit['key']}{'-' + insert if insert else ''}.zip",
                        "title": f"{kit['key']} kit" + (f" · {insert} insert" if insert else ""),
                        "files": ([file] if file else []) + kit["files"],
                        "slot": {"kit": kit["key"], "insert": insert}})
    out.append({"name": "frederick-all.zip", "title": "Every base and hopper part",
                "files": list(labels), "slot": {}})
    return out


def readme_text(bundle, manifest):
    """The README.txt that goes into a bundle: parts, material, print orientation and settings, links.

    Args:
        bundle: One entry of bundles().
        manifest: Manifest dict written by generate.py.

    Returns:
        Plain text, LF line endings.
    """
    items = {it["file"]: it for g in manifest["groups"] for it in g["items"]}
    lines = [f"frederick - {bundle['title'].replace(' · ', ', ')}",
             "Parametric, 3D-printable accessories for the Lelit Fred (PL043MMI) grinder.",
             "",
             "Every STL is in millimetres and already in print orientation: print it as it loads",
             "(z=0 on the bed). No part needs supports.",
             ""]
    if bundle["slot"].get("kit"):
        lines += ["The parts fit together bottom up, in the order listed.", ""]
    for f in bundle["files"]:
        it = items[f]
        size = " x ".join(f"{v:g}" for v in it["size_mm"])
        note = [f"  Note:     {it['material_note']}"] if it.get("material_note") else []
        lines += [f"{f}", f"  Part:     {it['label']}", f"  Material: {it['material']}", *note,
                  f"  Print:    {it['hint']}", f"  Size:     {size} mm, {it['volume_cm3']:g} cm3", ""]
    lines += ["The grinder figures behind these parts are estimates: measure your grinder and",
              "rebuild if they differ (see the README on GitHub).",
              "",
              f"Source and docs: {REPO_URL}",
              f"Edit the parameters: {REPO_URL}/blob/main/config.py",
              "License: GPL-3.0", ""]
    return "\n".join(lines)


def write_bundle(path, files, readme, stl_dir):
    """Write one deterministic zip: the STLs plus README.txt.

    Entries are sorted by name, stamped ZIP_DATE, mode 0644 and deflated at level 9, so the
    same inputs always give the same bytes.

    Args:
        path: Zip file to write.
        files: STL file names inside stl_dir.
        readme: README.txt text.
        stl_dir: Folder holding the STLs.
    """
    entries = {"README.txt": readme.encode("utf-8")}
    for f in files:
        with open(os.path.join(stl_dir, f), "rb") as fh:
            entries[f] = fh.read()
    with zipfile.ZipFile(path, "w") as zf:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, entries[name], compresslevel=9)


def _file_row(it, file_bytes, meta=False):
    """One STL row: label, material and print hint, material note if any, file name, size, GitHub link, download link.

    Args:
        it: Manifest part entry.
        file_bytes: STL size in bytes.
        meta: Also show the part size, volume and triangle count.

    Returns:
        HTML string of one <li>.
    """
    f, size = it["file"], fmt_bytes(file_bytes)
    dims = " × ".join(f"{v:g}" for v in it["size_mm"])
    note = (f'<span class="dl-note">{html.escape(it["material_note"])}</span>'
            if it.get("material_note") else "")
    extra = (f'<span class="dl-meta">{dims} mm · {it["volume_cm3"]:g} cm³ · {it["triangles"]} triangles</span>'
             if meta else "")
    return (f'<li class="dl-row"><div class="dl-what"><span class="dl-name">{html.escape(it["label"])}</span>'
            f'<span class="dl-mat"><b>{html.escape(it["material"])}</b> · {html.escape(it["hint"])}</span>{note}'
            f'<span class="dl-file"><code>{html.escape(f)}</code> {size} · '
            f'<a class="gh" href="{html.escape(github_url(f))}" target="_blank" rel="noopener noreferrer" '
            f'aria-label="View {html.escape(f)} on GitHub">view on GitHub</a></span>{extra}</div>'
            f'<a class="dl-get" href="stl/{urllib.parse.quote(f)}" download '
            f'aria-label="Download {html.escape(f)}, {size}">STL</a></li>')


def _zip_button(bundle, zip_bytes, text):
    """The big download button of one bundle.

    Args:
        bundle: One entry of bundles().
        zip_bytes: Zip size in bytes.
        text: Button text.

    Returns:
        HTML string of one <a>.
    """
    n = len(bundle["files"])
    return (f'<a class="dl-all" href="bundles/{urllib.parse.quote(bundle["name"])}" download>{text} '
            f'<span class="dl-sum">{n} STL{"" if n == 1 else "s"} + README, {fmt_bytes(zip_bytes)}</span></a>')


def print_html(manifest, bundle_list, sizes):
    """Render the "Print these" sets: one per base variant and per kit and insert, the default base shown.

    The page script shows the set of the slot last clicked (data-base, or data-kit + data-insert).

    Args:
        manifest: Manifest dict written by generate.py.
        bundle_list: bundles() of the manifest.
        sizes: File name (STL or zip) -> size in bytes.

    Returns:
        HTML string.
    """
    items = {it["file"]: it for g in manifest["groups"] for it in g["items"]}
    default = manifest["default"]["base"]
    out = []
    for b in bundle_list:
        slot = b["slot"]
        if not slot:
            continue
        attrs = (f'data-base="{html.escape(slot["base"])}"' if "base" in slot
                 else f'data-kit="{html.escape(slot["kit"])}" data-insert="{html.escape(slot["insert"])}"')
        hidden = "" if slot.get("base") == default else " hidden"
        out.append(f'<div class="print-set" {attrs} data-title="{html.escape(b["title"])}"{hidden}>'
                   f'<p class="fine dl-for">For <b>{html.escape(b["title"])}</b></p>'
                   + _zip_button(b, sizes[b["name"]], "Download bundle (.zip)")
                   + '<ul class="dl-list">'
                   + "".join(_file_row(items[f], sizes[f]) for f in b["files"]) + "</ul></div>")
    return "\n".join(out)


def downloads_html(manifest, bundle_list, sizes):
    """Render the full download list: everything as one zip, every bundle, then each STL once.

    Args:
        manifest: Manifest dict written by generate.py.
        bundle_list: bundles() of the manifest.
        sizes: File name (STL or zip) -> size in bytes.

    Returns:
        HTML string.
    """
    everything = next(b for b in bundle_list if not b["slot"])
    out = [_zip_button(everything, sizes[everything["name"]], "Download everything (.zip)"),
           '<h3 class="label">Bundles</h3><ul class="dl-list">']
    for b in bundle_list:
        if b["slot"]:
            name, size = html.escape(b["name"]), fmt_bytes(sizes[b["name"]])
            out.append(f'<li class="dl-row"><div class="dl-what"><span class="dl-name">{html.escape(b["title"])}</span>'
                       f'<span class="dl-file"><code>{name}</code> {size}</span></div>'
                       f'<a class="dl-get" href="bundles/{urllib.parse.quote(b["name"])}" download '
                       f'aria-label="Download {name}, {size}">.zip</a></li>')
    out.append("</ul>")
    for group in manifest["groups"]:
        out.append(f'<h3 class="label">{html.escape(group["name"])}</h3><ul class="dl-list">')
        out.extend(_file_row(it, sizes[it["file"]], meta=True) for it in group["items"])
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
    """Write index.html, the listed STLs, the zip bundles and .nojekyll into out_dir.

    Args:
        root: Folder holding build/manifest.json and stl/.
        out_dir: Site folder; deleted and recreated.
        template: Page template with every PLACEHOLDERS entry.

    Raises:
        SystemExit: The manifest, a listed STL, the ghost STL or a template
            placeholder is missing.
    """
    manifest_path = os.path.join(root, "build", "manifest.json")
    if not os.path.exists(manifest_path):
        raise SystemExit(f"{manifest_path} not found - run generate.py (make generate) first")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(template, encoding="utf-8") as f:
        page = f.read()
    for key in PLACEHOLDERS:
        if key not in page:
            raise SystemExit(f"{template} has no {key} placeholder")
    stl_dir = os.path.join(root, "stl")
    files = [it["file"] for g in manifest["groups"] for it in g["items"]]
    ghost = manifest["ghost"]["file"]
    missing = [f"stl/{f}" for f in files if not os.path.exists(os.path.join(stl_dir, f))]
    if not os.path.exists(os.path.join(root, "build", ghost)):
        missing.append(f"build/{ghost}")
    if missing:
        raise SystemExit(f"files listed in the manifest are missing (run generate.py): {', '.join(missing)}")

    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(os.path.join(out_dir, "stl"))
    os.makedirs(os.path.join(out_dir, "bundles"))
    sizes = {}
    for f in files:
        shutil.copy2(os.path.join(stl_dir, f), os.path.join(out_dir, "stl", f))
        sizes[f] = os.path.getsize(os.path.join(stl_dir, f))
    bundle_list = bundles(manifest)
    for b in bundle_list:
        path = os.path.join(out_dir, "bundles", b["name"])
        write_bundle(path, b["files"], readme_text(b, manifest), stl_dir)
        sizes[b["name"]] = os.path.getsize(path)

    fills = {
        # inside <script type="application/json">: only "</" could end the element early
        "@MANIFEST@": json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/"),
        "@DOWNLOADS@": downloads_html(manifest, bundle_list, sizes),
        "@PRINT@": print_html(manifest, bundle_list, sizes),
        "@PARAMETERS@": parameters_html(manifest),
        "@MESHES@": meshes_html(stl_dir, files) + "\n" + meshes_html(os.path.join(root, "build"), [ghost]),
        "@REPO@": REPO_URL,
    }
    for key, value in fills.items():
        page = page.replace(key, value)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()


if __name__ == "__main__":
    build_site(ROOT, os.path.join(ROOT, "_site"))
    size = os.path.getsize(os.path.join(ROOT, "_site", "index.html"))
    n = len(os.listdir(os.path.join(ROOT, "_site", "bundles")))
    print(f"_site/index.html ({size / 1e6:.2f} MB, opens from disk; no server needed), {n} zip bundles")
