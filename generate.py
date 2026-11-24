"""Build every frederick part into stl/ and write build/manifest.json.

    python3 generate.py [--angle DEG] [--set NAME=VALUE ...]

Meshes are in mm, in print orientation, with z=0 on the bed; each one must be
watertight before it is exported. tools/build_site.py turns the manifest
into the preview page.
"""

import argparse
import json
import os

from geometry.common import add_cli_args, config_from_args

ROOT = os.path.dirname(os.path.abspath(__file__))

# kind -> (material, print hint)
PRINT_INFO = {
    "base": ("PLA/PETG", "4 walls, 20-30 % infill, no supports, deck up"),
    "insert": ("PLA/PETG", "spout down, no supports"),
    "bellows": ("TPU 95A", "cap on the bed, no supports; 3+ walls or 100 % infill is fine"),
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
    from geometry.hopper import build_bellows, build_insert

    parts = []
    for name, flags in cfg.BASE_VARIANTS.items():
        parts.append(("Angled base", f"frederick-base-{name}.stl", _pretty(name), "base",
                      build_base(cfg, frame=flags["frame"], window=flags["window"])))
    for name, flags in cfg.INSERT_VARIANTS.items():
        parts.append(("Single-dose hopper", f"frederick-hopper-insert-{name}.stl", f"Insert, {name}",
                      "insert", build_insert(cfg, screw_hub=flags["screw_hub"])))
    parts.append(("Single-dose hopper", "frederick-hopper-bellows.stl", "Bellows", "bellows",
                  build_bellows(cfg)))
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


def build_manifest(cfg, entries):
    """Group part entries and add the parameter table.

    Args:
        cfg: Config namespace from load_config().
        entries: List of (group, part_entry dict), in display order.

    Returns:
        Manifest dict: {"groups": [{"name", "items"}], "parameters": [[name, value]]}.
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
            "parameters": parameters}


def main(argv=None):
    """Build the STLs and the manifest.

    Args:
        argv: Command-line arguments (default: sys.argv[1:]).
    """
    parser = add_cli_args(argparse.ArgumentParser(description=__doc__.splitlines()[0]))
    cfg = config_from_args(parser.parse_args(argv))
    os.makedirs(os.path.join(ROOT, "stl"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    entries = []
    for group, file, label, kind, mesh in build_parts(cfg):
        entry = part_entry(mesh, file, label, kind)
        mesh.export(os.path.join(ROOT, "stl", file))
        entries.append((group, entry))
        size = " × ".join(f"{v:g}" for v in entry["size_mm"])
        print(f"stl/{file}: {size} mm, {entry['volume_cm3']} cm³, {entry['triangles']} triangles")
    with open(os.path.join(ROOT, "build", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(build_manifest(cfg, entries), f, indent=2, ensure_ascii=False)
    print("build/manifest.json")


if __name__ == "__main__":
    main()
