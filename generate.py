"""Build every frederick part into stl/ and write build/manifest.json.

    python3 generate.py [--angle DEG] [--set NAME=VALUE ...]

Meshes are in mm, in print orientation, with z=0 on the bed; each one must be
watertight before it is exported. The grinder ghost (preview context only, not
a part) goes to build/, never stl/. tools/build_site.py turns the manifest
into the preview page.
"""

import argparse
import json
import os

import numpy as np

from geometry.common import add_cli_args, config_from_args

ROOT = os.path.dirname(os.path.abspath(__file__))
GHOST_FILE = "frederick-grinder-ghost.stl"  # in build/: preview only, never a download

# kind -> (material, print hint)
PRINT_INFO = {
    "base": ("PLA/PETG", "4 walls, 20-30 % infill, no supports, deck up"),
    "insert": ("PLA/PETG", "spout down, no supports"),
    "bellows": ("TPU 95A", "cap on the bed, no supports; 3+ walls or 100 % infill is fine"),
    "2p-body": ("TPU 95A", "spout down, no supports"),
    "2p-cap": ("PLA/PETG", "top face down, no supports"),
}


def build_parts(cfg):
    """Build every part.

    The geometry modules are imported here, so this file imports even while
    they are missing.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        List of (group, file, label, kind, trimesh.Trimesh).
    """
    from geometry.base import build_base
    from geometry.hopper import build_bellows, build_insert, build_two_piece_body, build_two_piece_cap

    parts = []
    for name, flags in cfg.BASE_VARIANTS.items():
        parts.append(("Angled base", f"frederick-base-{name}.stl", _pretty(name), "base",
                      build_base(cfg, frame=flags["frame"], window=flags["window"])))
    hopper = "Single-dose hopper"
    for name, flags in cfg.INSERT_VARIANTS.items():
        parts.append((hopper, f"frederick-hopper-insert-{name}.stl", f"Insert + bellows: {name} insert",
                      "insert", build_insert(cfg, screw_hub=flags["screw_hub"])))
    parts.append((hopper, "frederick-hopper-bellows.stl", "Insert + bellows: bellows", "bellows",
                  build_bellows(cfg)))
    parts.append((hopper, "frederick-hopper-2p-body.stl", "Two-piece: body", "2p-body", build_two_piece_body(cfg)))
    parts.append((hopper, "frederick-hopper-2p-cap.stl", "Two-piece: cap", "2p-cap", build_two_piece_cap(cfg)))
    return parts


def _pretty(name):
    """Turn a variant key into a button label.

    Args:
        name: Variant key such as "frame-window".

    Returns:
        Label such as "Frame + window".
    """
    return name.replace("-", " + ").capitalize()


def part_entry(mesh, file, label, kind):
    """Check one built mesh and describe it for the manifest.

    Args:
        mesh: trimesh.Trimesh of the part.
        file: STL file name inside stl/.
        label: Short human label.
        kind: Key of PRINT_INFO.

    Returns:
        Dict with file, label, material, hint, size_mm, volume_cm3, triangles.

    Raises:
        ValueError: The mesh is not watertight or does not sit on z=0.
    """
    if not mesh.is_watertight:
        raise ValueError(f"{file}: mesh is not watertight")
    if abs(mesh.bounds[0][2]) > 1e-3:
        raise ValueError(f"{file}: lowest point is z={mesh.bounds[0][2]:.4f}, expected 0 (on the bed)")
    material, hint = PRINT_INFO[kind]
    return {
        "file": file,
        "label": label,
        "material": material,
        "hint": hint,
        "size_mm": [round(float(v), 1) for v in mesh.extents],
        "volume_cm3": round(float(mesh.volume) / 1000.0, 2),
        "triangles": int(len(mesh.faces)),
    }


def row_major(matrix):
    """Flatten a 4x4 matrix for the manifest.

    Row-major, so the page reads it with three.js Matrix4.set(...m);
    Matrix4.fromArray() expects column-major and would transpose it.

    Args:
        matrix: 4x4 array-like.

    Returns:
        List of 16 floats, rounded to 6 decimals.
    """
    return [round(float(v), 6) for v in np.asarray(matrix, dtype=float).ravel()]


def kit_partners(cfg, kind):
    """The parts the preview shows faintly with this one, so the hopper looks complete.

    Args:
        cfg: Config namespace from load_config().
        kind: Key of PRINT_INFO.

    Returns:
        List of STL file names (empty for the base).
    """
    insert = f"frederick-hopper-insert-{next(iter(cfg.INSERT_VARIANTS))}.stl"
    return {"insert": ["frederick-hopper-bellows.stl"], "bellows": [insert],
            "2p-body": ["frederick-hopper-2p-cap.stl"], "2p-cap": ["frederick-hopper-2p-body.stl"]}.get(kind, [])


def view_fields(cfg, file, kind):
    """Where the part and the grinder ghost go in the preview's "Show on grinder" view.

    A base stays put and the ghost stands in its pockets; a hopper part is
    posed into the throat of the ghost standing upright on the table.

    Args:
        cfg: Config namespace from load_config().
        file: STL file name; for hopper parts its stem keys assembly_poses().
        kind: Key of PRINT_INFO.

    Returns:
        Dict with placement and ghost_placement (row_major() 4x4s, from the
        STL's own frame into the view) and partners (kit_partners()).
    """
    from geometry.grinder import grinder_on_base_pose, grinder_upright_pose, throat_pose
    from geometry.hopper import assembly_poses

    if kind == "base":
        part, ghost = np.eye(4), grinder_on_base_pose(cfg)
    else:
        ghost = grinder_upright_pose(cfg)
        part = ghost @ throat_pose(cfg) @ assembly_poses(cfg)[file.removesuffix(".stl")]
    return {"placement": row_major(part), "ghost_placement": row_major(ghost), "partners": kit_partners(cfg, kind)}


def build_manifest(cfg, entries):
    """Group part entries and add the parameter table.

    Args:
        cfg: Config namespace from load_config().
        entries: List of (group, part_entry dict), in display order.

    Returns:
        Manifest dict: {"groups": [{"name", "items"}], "parameters": [[name, value]],
        "ghost": {"file"}} (the ghost STL lives in build/).
    """
    groups = {}
    for group, entry in entries:
        groups.setdefault(group, []).append(entry)
    c = cfg
    parameters = [
        ["Base angle", f"{c.BASE_ANGLE:g}°"],
        ["Deck height at the front", f"{c.BASE_FRONT_H:g} mm"],
        ["Grinder plate (W × D)", f"{c.GRINDER_PLATE_W:g} × {c.GRINDER_PLATE_D:g} mm"],
        ["Foot (Ø × height)", f"{c.FOOT_D:g} × {c.FOOT_H:g} mm"],
        ["Foot spacing (L-R × front-back)", f"{c.FOOT_SPACING_X:g} × {c.FOOT_SPACING_Y:g} mm"],
        ["Throat ID", f"{c.THROAT_ID:g} mm"],
        ["Spout OD", f"{c.THROAT_ID - c.SPOUT_CLEARANCE:g} mm"],
        ["Bellows OD", f"{c.BELLOWS_OD:g} mm"],
        ["Bellows folds", f"{c.BELLOWS_FOLDS}"],
    ]
    return {"groups": [{"name": g, "items": items} for g, items in groups.items()],
            "parameters": parameters, "ghost": {"file": GHOST_FILE}}


def main(argv=None):
    """Build the STLs, the grinder ghost (build/) and the manifest.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).
    """
    parser = add_cli_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    cfg = config_from_args(parser.parse_args(argv))
    os.makedirs(os.path.join(ROOT, "stl"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    entries = []
    for group, file, label, kind, mesh in build_parts(cfg):
        entry = part_entry(mesh, file, label, kind) | view_fields(cfg, file, kind)
        mesh.export(os.path.join(ROOT, "stl", file))
        entries.append((group, entry))
        size = " × ".join(f"{v:g}" for v in entry["size_mm"])
        print(f"stl/{file}: {size} mm, {entry['volume_cm3']} cm³, {entry['triangles']} triangles")
    from geometry.grinder import build_grinder_ghost

    build_grinder_ghost(cfg).export(os.path.join(ROOT, "build", GHOST_FILE))
    print(f"build/{GHOST_FILE}: approximate grinder, preview context only")
    with open(os.path.join(ROOT, "build", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(build_manifest(cfg, entries), f, indent=2, ensure_ascii=False)
    print("build/manifest.json")


if __name__ == "__main__":
    main()
