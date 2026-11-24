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

DEFAULT_BASE = "frame-solid"  # base the preview's final form starts on (else the first BASE_VARIANTS entry)

_SCREW_NOTE = ("PETG or ASA: PLA slowly creeps under a constant screw clamp and the screw works loose. "
               "Use 5+ walls or 100 % infill around the hub, use a washer, and tighten only until snug.")
_TPU_NOTE = ("TPU 95A; 85A pumps more easily but is harder to print. Print slowly (20-30 mm/s), with 2-3 walls "
             "and minimal retraction. Food-safe TPU is available if you want it.")
# kind -> (material, print hint, material note: 1-3 practical sentences the page shows with the part)
PRINT_INFO = {
    "base": ("PLA/PETG", "4 walls, 20-30 % infill, no supports, deck up",
             "PLA or PETG; prefer PETG or ASA if it sits near a hot espresso machine. 4 walls, 20-30 % gyroid "
             "infill, no supports. Stick Ø12.7 mm silicone bumpers in the pad recesses."),
    "insert-friction": ("PLA/PETG", "spout down, no supports",
                        "PETG, or PLA+; a food-safe PETG is the best choice for bean contact. PLA-CF looks like the "
                        "commercial parts but needs a hardened nozzle. Wash by hand only, no dishwasher."),
    "insert-screw": ("PETG/ASA", "spout down, no supports", _SCREW_NOTE),
    "insert-screw-reinforced": ("PETG/ASA", "spout down, no supports",
                                _SCREW_NOTE + " The stronger choice if you clamp with the stock screw; still check "
                                              "the screw's length and thread first."),
    "bellows-capped": ("TPU 95A", "cap on the bed, no supports", _TPU_NOTE),
    "bellows-open": ("TPU 95A", "ring on the bed, no supports", _TPU_NOTE),
    "2p-body": ("TPU 95A", "spout down, no supports",
                "TPU 95A; 98A gives a stiffer spout if the friction fit feels loose. The same slow settings as the "
                "bellows: 20-30 mm/s, 2-3 walls, minimal retraction."),
    "cap": ("PLA/PETG", "top face down, no supports", "PETG or PLA, 100 % infill since it's thin, top face down."),
}


def build_parts(cfg):
    """Build every part, each once (kits share the insert and the cap).

    The geometry modules are imported here, so this file imports even while
    they are missing.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        List of (group, file, label, kind, trimesh.Trimesh).
    """
    from geometry.base import build_base
    from geometry.hopper import build_bellows, build_bellows_open, build_cap, build_insert, build_two_piece_body

    parts = []
    for name, flags in cfg.BASE_VARIANTS.items():
        parts.append(("Angled base", f"frederick-base-{name}.stl", _pretty(name), "base",
                      build_base(cfg, frame=flags["frame"], window=flags["window"])))
    hopper = "Single-dose hopper"
    for name, flags in cfg.INSERT_VARIANTS.items():
        parts.append((hopper, f"frederick-hopper-insert-{name}.stl", f"Insert: {name}", insert_kind(flags),
                      build_insert(cfg, **flags)))
    for kind, label, build in [("bellows-capped", "Capped bellows", build_bellows),
                               ("bellows-open", "Open bellows", build_bellows_open),
                               ("2p-body", "Two-piece body", build_two_piece_body),
                               ("cap", "Cap", build_cap)]:
        parts.append((hopper, f"frederick-hopper-{kind}.stl", label, kind, build(cfg)))
    return parts


def insert_kind(flags):
    """PRINT_INFO key for an insert, from its INSERT_VARIANTS flags (not its name, so any variant works).

    Args:
        flags: INSERT_VARIANTS entry, build_insert() keywords: screw_hub, optional reinforced.

    Returns:
        "insert-friction", "insert-screw" or "insert-screw-reinforced".
    """
    if not flags["screw_hub"]:
        return "insert-friction"
    return "insert-screw-reinforced" if flags.get("reinforced") else "insert-screw"


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
        Dict with file, label, material, hint, material_note, size_mm, volume_cm3, triangles.

    Raises:
        ValueError: The mesh is not watertight or does not sit on z=0.
    """
    if not mesh.is_watertight:
        raise ValueError(f"{file}: mesh is not watertight")
    if abs(mesh.bounds[0][2]) > 1e-3:
        raise ValueError(f"{file}: lowest point is z={mesh.bounds[0][2]:.4f}, expected 0 (on the bed)")
    material, hint, note = PRINT_INFO[kind]
    return {
        "file": file,
        "label": label,
        "material": material,
        "hint": hint,
        "material_note": note,
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


def final_form(cfg):
    """What the preview's "Show on grinder" view draws: a base, the ghost on it, a hopper kit in its throat.

    Placements are row_major() 4x4s from an STL's own frame into the base's
    world frame. A base stays put, the ghost stands in its pockets
    (grinder_on_base_pose) and each kit part goes to
    grinder_on_base_pose @ throat_pose @ its kit pose. None depends on the base variant.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        Dict with ghost ({file, placement}), bases ({variant: file}), kits
        (one {key, inserts: {variant: file} or {}, files: the other parts
        bottom up, placements: {file: matrix}} per HOPPER_KITS entry, every
        insert variant placed) and default ({base, kit, insert}).

    Raises:
        ValueError: A kit is inconsistent (see hopper.kit_poses()).
    """
    from geometry.grinder import grinder_on_base_pose, throat_pose
    from geometry.hopper import kit_poses

    ghost = grinder_on_base_pose(cfg)
    throat = ghost @ throat_pose(cfg)
    bases = {name: f"frederick-base-{name}.stl" for name in cfg.BASE_VARIANTS}
    inserts = {name: f"frederick-hopper-insert-{name}.stl" for name in cfg.INSERT_VARIANTS}
    kits = []
    for key, poses in kit_poses(cfg).items():
        files = {part: list(inserts.values()) if part == "insert" else [f"frederick-hopper-{part}.stl"]
                 for part in poses}
        kits.append({"key": key, "inserts": inserts if "insert" in poses else {},
                     "files": [f for part, fs in files.items() if part != "insert" for f in fs],
                     "placements": {f: row_major(throat @ poses[part]) for part, fs in files.items() for f in fs}})
    default = {"base": DEFAULT_BASE if DEFAULT_BASE in bases else next(iter(bases)),
               "kit": kits[0]["key"], "insert": next(iter(inserts))}
    return {"ghost": {"file": GHOST_FILE, "placement": row_major(ghost)}, "bases": bases, "kits": kits,
            "default": default}


def build_manifest(cfg, entries):
    """Group part entries and add the parameter table.

    Args:
        cfg: Config namespace from load_config().
        entries: List of (group, part_entry dict), in display order.

    Returns:
        Manifest dict: {"groups": [{"name", "items"}], "parameters": [[name, value]]}
        plus final_form()'s ghost (its STL lives in build/), bases, kits and default.
        Each STL is in one group only, so the downloads list it once.
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
            "parameters": parameters} | final_form(cfg)


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
        entry = part_entry(mesh, file, label, kind)
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
