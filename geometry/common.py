"""Shared helpers: config loading with CLI overrides, and shapely -> manifold3d -> trimesh."""

import ast
import copy
import difflib
import types

import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, Manifold


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def load_config(overrides=None):
    """Snapshot config.py's UPPER_CASE names, apply overrides, validate.

    Args:
        overrides: Optional dict NAME -> value replacing config.py defaults.

    Returns:
        types.SimpleNamespace with one attribute per config constant.

    Raises:
        SystemExit: An override names an unknown constant, or gives a
            non-number for a numeric constant.
        ValueError: The resulting values fail validate().
    """
    import config

    values = {n: copy.deepcopy(getattr(config, n)) for n in dir(config) if n.isupper()}
    for name, value in (overrides or {}).items():
        if name not in values:
            close = difflib.get_close_matches(name, values, n=3)
            hint = f" - did you mean {', '.join(close)}?" if close else " (see config.py)"
            raise SystemExit(f"unknown config name {name!r}{hint}")
        default = values[name]
        if isinstance(default, (int, float)) and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise SystemExit(f"{name} must be a number, got {value!r}")
        values[name] = value
    cfg = types.SimpleNamespace(**values)
    validate(cfg)
    return cfg


def validate(cfg):
    """Reject parameter combinations that cannot produce a sane part.

    Args:
        cfg: Config namespace from load_config().

    Raises:
        ValueError: Lists every failed check.
    """
    spout_id = cfg.THROAT_ID - cfg.SPOUT_CLEARANCE - 2 * cfg.SPOUT_WALL
    checks = [
        (0 < cfg.BASE_ANGLE <= 30, "BASE_ANGLE must be in (0, 30] deg"),
        (cfg.BASE_EDGE_MARGIN - cfg.FRAME_GAP >= 2,
         "frame wall BASE_EDGE_MARGIN - FRAME_GAP must be >= 2 mm"),
        (0 < cfg.POCKET_DEPTH < cfg.FOOT_H, "POCKET_DEPTH must be > 0 and < FOOT_H"),
        (spout_id > 0, "spout ID THROAT_ID - SPOUT_CLEARANCE - 2 * SPOUT_WALL must be > 0"),
        (2 * cfg.BELLOWS_FOLD_DEPTH < cfg.BELLOWS_OD, "2 * BELLOWS_FOLD_DEPTH must be < BELLOWS_OD"),
        (cfg.SEGMENTS >= 16, "SEGMENTS must be >= 16"),
        (bool(cfg.BASE_VARIANTS) and bool(cfg.INSERT_VARIANTS) and bool(cfg.HOPPER_KITS),
         "BASE_VARIANTS, INSERT_VARIANTS and HOPPER_KITS must not be empty"),
    ]
    errors = [msg for ok, msg in checks if not ok]
    if errors:
        raise ValueError("config error:\n  " + "\n  ".join(errors))


def add_cli_args(parser):
    """Add the config override options to an argparse parser.

    Args:
        parser: argparse.ArgumentParser to extend.

    Returns:
        The same parser.
    """
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                        help="override any config.py constant (Python literal), repeatable")
    parser.add_argument("--angle", type=float, metavar="DEG", help="shortcut for --set BASE_ANGLE=DEG")
    return parser


def config_from_args(args):
    """Turn parsed CLI arguments into a validated config.

    Args:
        args: Namespace from a parser extended by add_cli_args().

    Returns:
        types.SimpleNamespace from load_config().

    Raises:
        SystemExit: A --set item has no '=' or names an unknown constant.
    """
    overrides = {}
    for item in args.set:
        if "=" not in item:
            raise SystemExit(f"--set expects NAME=VALUE, got {item!r}")
        name, text = (s.strip() for s in item.split("=", 1))
        try:
            overrides[name] = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            overrides[name] = text
    if args.angle is not None:
        overrides["BASE_ANGLE"] = args.angle
    return load_config(overrides)


# ---------------------------------------------------------------------------
# mesh
# ---------------------------------------------------------------------------

def _cross_section(polygon):
    """Convert a shapely Polygon/MultiPolygon to a manifold3d CrossSection.

    Even-odd fill, so ring orientation does not matter (GEOS output is clockwise).

    Args:
        polygon: shapely Polygon or MultiPolygon (holes allowed).

    Returns:
        manifold3d.CrossSection.
    """
    contours = []
    for p in getattr(polygon, "geoms", [polygon]):
        contours.append(np.asarray(p.exterior.coords)[:-1])
        contours += [np.asarray(ring.coords)[:-1] for ring in p.interiors]
    return CrossSection(contours, FillRule.EvenOdd)


def prism(polygon, z0, z1):
    """Extrude a plan-view outline into a vertical prism.

    Args:
        polygon: shapely Polygon or MultiPolygon in the XY plane.
        z0: Bottom height (mm).
        z1: Top height (mm), > z0.

    Returns:
        manifold3d.Manifold spanning z0..z1.
    """
    return Manifold.extrude(_cross_section(polygon), float(z1 - z0)).translate((0.0, 0.0, float(z0)))


def revolve(profile, segments):
    """Revolve an (r, z) profile 360 degrees about the Z axis.

    manifold3d revolves a cross-section about its Y axis and makes that the
    Z axis, so profile x is the radius and profile y stays z.

    Args:
        profile: shapely Polygon in the (r, z) half-plane, r >= 0.
        segments: Number of segments around the full circle.

    Returns:
        manifold3d.Manifold, the solid of revolution.
    """
    return _cross_section(profile).revolve(int(segments))


def to_trimesh(m):
    """Convert a manifold3d Manifold to a trimesh Trimesh.

    Args:
        m: manifold3d.Manifold.

    Returns:
        trimesh.Trimesh with merged vertices.
    """
    mesh = m.to_mesh64()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)
