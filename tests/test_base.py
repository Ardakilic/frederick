"""Tests for the angled base stand (geometry/base.py), measured with vertical rays."""

import math

import numpy as np
import pytest
from manifold3d import Manifold, Mesh64

from geometry.base import build_base
from geometry.common import load_config

CFG = load_config()
VARIANTS = CFG.BASE_VARIANTS
FRAMED = [name for name, flags in VARIANTS.items() if flags["frame"]]


@pytest.fixture(scope="module")
def bases():
    """Every default variant, built once.

    Returns:
        Dict variant name -> trimesh.Trimesh.
    """
    return {name: build_base(CFG, **flags) for name, flags in VARIANTS.items()}


def dims(cfg):
    """Derived layout numbers, computed independently of geometry/base.py.

    Args:
        cfg: Config namespace.

    Returns:
        Dict with a (rad), wd, ld, lf, rise, wall, r (pocket radius), feet [(x, u)].
    """
    a = math.radians(cfg.BASE_ANGLE)
    ld = cfg.GRINDER_PLATE_D + 2 * cfg.BASE_EDGE_MARGIN
    return {
        "a": a,
        "wd": cfg.GRINDER_PLATE_W + 2 * cfg.BASE_EDGE_MARGIN,
        "ld": ld,
        "lf": ld * math.cos(a),
        "rise": cfg.FOOT_H - cfg.POCKET_DEPTH + cfg.FRAME_OVERLAP,
        "wall": cfg.BASE_EDGE_MARGIN - cfg.FRAME_GAP,
        "r": (cfg.FOOT_D + cfg.FOOT_CLEARANCE) / 2,
        "feet": [(sx * cfg.FOOT_SPACING_X / 2, ld / 2 + sy * cfg.FOOT_SPACING_Y / 2)
                 for sx in (-1, 1) for sy in (-1, 1)],
    }


def hits(mesh, x, y):
    """Heights where a vertical ray through (x, y) crosses the surface.

    Args:
        mesh: trimesh.Trimesh.
        x: World X.
        y: World Y.

    Returns:
        List of z values, highest first (empty if the ray misses).
    """
    loc, _, _ = mesh.ray.intersects_location([[x, y, 1000.0]], [[0.0, 0.0, -1.0]])
    return sorted((float(p[2]) for p in loc), reverse=True)


def deck_z(cfg, y):
    """Expected deck height at world Y.

    Args:
        cfg: Config namespace.
        y: World Y.

    Returns:
        Height in mm.
    """
    return cfg.BASE_FRONT_H + y * math.tan(math.radians(cfg.BASE_ANGLE))


def measure_deck(cfg, mesh):
    """Measure the deck slope on a line beside the window, inside any frame.

    Args:
        cfg: Config namespace.
        mesh: trimesh.Trimesh of a base.

    Returns:
        (angle in degrees, extrapolated deck height at Y=0).
    """
    d = dims(cfg)
    x = (d["wd"] / 2 - cfg.WINDOW_SIDE_RAIL + cfg.GRINDER_PLATE_W / 2 + cfg.FRAME_GAP) / 2
    y1, y2 = 0.35 * d["lf"], 0.65 * d["lf"]
    z1, z2 = hits(mesh, x, y1)[0], hits(mesh, x, y2)[0]
    slope = (z2 - z1) / (y2 - y1)
    return math.degrees(math.atan(slope)), z1 - y1 * slope


def to_world(cfg, m):
    """Map a deck-frame (x, u, w) Manifold to world coordinates.

    Args:
        cfg: Config namespace.
        m: manifold3d.Manifold in deck coordinates.

    Returns:
        manifold3d.Manifold in world coordinates.
    """
    a = math.radians(cfg.BASE_ANGLE)
    c, s = math.cos(a), math.sin(a)
    return m.transform([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, cfg.BASE_FRONT_H]])


@pytest.mark.parametrize("name", VARIANTS)
def test_mesh_is_printable_solid(name, bases):
    """Watertight single body on the bed with the expected footprint.

    Args:
        name: Variant key from BASE_VARIANTS.
        bases: Fixture: variant name -> built base mesh.
    """
    mesh, d = bases[name], dims(CFG)
    assert mesh.is_watertight
    assert len(mesh.split(only_watertight=False)) == 1
    assert mesh.volume > 0
    assert mesh.bounds[0][2] == pytest.approx(0, abs=1e-6)
    assert mesh.extents[:2].tolist() == pytest.approx([d["wd"], d["lf"]], abs=0.05)


@pytest.mark.parametrize("name", VARIANTS)
def test_no_steep_overhangs(name, bases):
    """Only the bed face and the pad recess ceilings face down more than 45 deg from vertical.

    Args:
        name: Variant key from BASE_VARIANTS.
        bases: Fixture: variant name -> built base mesh.
    """
    mesh = bases[name]
    z = mesh.triangles_center[:, 2]
    steep = mesh.face_normals[:, 2] < -math.sqrt(0.5)
    assert np.all(np.isclose(z[steep], 0) | np.isclose(z[steep], CFG.PAD_DEPTH))


@pytest.mark.parametrize("name", VARIANTS)
def test_deck_angle_and_front_height(name, bases):
    """The deck rises at BASE_ANGLE and starts at BASE_FRONT_H.

    Args:
        name: Variant key from BASE_VARIANTS.
        bases: Fixture: variant name -> built base mesh.
    """
    angle, front = measure_deck(CFG, bases[name])
    assert angle == pytest.approx(CFG.BASE_ANGLE, abs=0.05)
    assert front == pytest.approx(CFG.BASE_FRONT_H, abs=0.01)


@pytest.mark.parametrize("name", VARIANTS)
def test_foot_pockets(name, bases):
    """Each pocket floor sits POCKET_DEPTH below the deck; its diameter is right.

    Args:
        name: Variant key from BASE_VARIANTS.
        bases: Fixture: variant name -> built base mesh.
    """
    mesh, d = bases[name], dims(CFG)
    for x, u in d["feet"]:
        y = u * math.cos(d["a"])
        floor = deck_z(CFG, y) - CFG.POCKET_DEPTH / math.cos(d["a"])
        for dx in (0.0, d["r"] - 0.3, -(d["r"] - 0.3)):
            assert hits(mesh, x + dx, y)[0] == pytest.approx(floor, abs=1e-3)
        for dx in (d["r"] + CFG.POCKET_CHAMFER + 0.5, -(d["r"] + CFG.POCKET_CHAMFER + 0.5)):
            assert hits(mesh, x + dx, y)[0] == pytest.approx(deck_z(CFG, y), abs=1e-3)


@pytest.mark.parametrize("name", VARIANTS)
def test_window(name, bases):
    """Window variants are open at the deck centre, solid ones are not.

    Args:
        name: Variant key from BASE_VARIANTS.
        bases: Fixture: variant name -> built base mesh.
    """
    y = dims(CFG)["lf"] / 2
    z = hits(bases[name], 0.0, y)
    if VARIANTS[name]["window"]:
        assert z == []
    else:
        assert z[0] == pytest.approx(deck_z(CFG, y), abs=1e-3)


@pytest.mark.parametrize("name", FRAMED)
def test_frame_rim_and_cable_notch(name, bases):
    """The rim stands RISE above the deck; the cable notch is cut down to the deck.

    Args:
        name: Variant key from BASE_VARIANTS.
        bases: Fixture: variant name -> built base mesh.
    """
    mesh, d = bases[name], dims(CFG)
    rim = d["rise"] / math.cos(d["a"])
    y = d["lf"] / 2
    assert hits(mesh, d["wd"] / 2 - d["wall"] / 2, y)[0] == pytest.approx(deck_z(CFG, y) + rim, abs=1e-3)
    y = (d["ld"] - d["wall"] / 2) * math.cos(d["a"])   # inside the back wall, at deck level
    assert hits(mesh, CFG.CABLE_NOTCH_X, y)[0] == pytest.approx(deck_z(CFG, y), abs=1e-3)
    beside = CFG.CABLE_NOTCH_X + CFG.CABLE_NOTCH_W / 2 + d["wall"]
    assert hits(mesh, beside, y)[0] == pytest.approx(deck_z(CFG, y) + rim, abs=1e-3)


@pytest.mark.parametrize("name", VARIANTS)
def test_grinder_fits(name, bases):
    """A ghost of the plate and feet, seated in the pockets, does not touch the base.

    Args:
        name: Variant key from BASE_VARIANTS.
        bases: Fixture: variant name -> built base mesh.
    """
    mesh, d = bases[name], dims(CFG)
    plate_w = CFG.FOOT_H - CFG.POCKET_DEPTH
    ghost = Manifold.cube((CFG.GRINDER_PLATE_W, CFG.GRINDER_PLATE_D, 2.0)).translate(
        (-CFG.GRINDER_PLATE_W / 2, (d["ld"] - CFG.GRINDER_PLATE_D) / 2, plate_w))
    for x, u in d["feet"]:
        ghost += Manifold.cylinder(CFG.FOOT_H, CFG.FOOT_D / 2, circular_segments=CFG.SEGMENTS).translate(
            (x, u, -CFG.POCKET_DEPTH))
    base = Manifold(Mesh64(vert_properties=np.ascontiguousarray(mesh.vertices, dtype=np.float64),
                           tri_verts=np.ascontiguousarray(mesh.faces, dtype=np.uint64)))
    assert (base ^ to_world(CFG, ghost)).volume() < 0.01
    # control: the same ghost pushed 0.5 mm into the deck does collide
    assert (base ^ to_world(CFG, ghost.translate((0, 0, -0.5)))).volume() > 1.0


def test_angle_parameter():
    """BASE_ANGLE drives the measured deck slope."""
    cfg = load_config({"BASE_ANGLE": 15.0})
    angle, _ = measure_deck(cfg, build_base(cfg, frame=False, window=False))
    assert angle == pytest.approx(15.0, abs=0.05)


def test_foot_spacing_moves_pockets(bases):
    """A wider FOOT_SPACING_X moves the pockets outward.

    Args:
        bases: Fixture: variant name -> built base mesh.
    """
    cfg = load_config({"FOOT_SPACING_X": CFG.FOOT_SPACING_X + 4})
    d = dims(cfg)
    x, u = d["feet"][-1]
    y = u * math.cos(d["a"])
    probe = x + d["r"] - 0.3       # inside the moved pocket, outside the default one
    floor = deck_z(cfg, y) - cfg.POCKET_DEPTH / math.cos(d["a"])
    assert hits(build_base(cfg, frame=False, window=False), probe, y)[0] == pytest.approx(floor, abs=1e-3)
    assert hits(bases["solid"], probe, y)[0] == pytest.approx(deck_z(cfg, y), abs=1e-3)


def test_pad_recesses(bases):
    """PAD_DEPTH > 0 recesses the bottom at each pad; 0 leaves it flat.

    Args:
        bases: Fixture: variant name -> built base mesh.
    """
    x = dims(CFG)["wd"] / 2 - CFG.PAD_INSET
    assert hits(bases["solid"], x, CFG.PAD_INSET)[-1] == pytest.approx(CFG.PAD_DEPTH, abs=1e-6)
    flat = build_base(load_config({"PAD_DEPTH": 0.0}), frame=False, window=False)
    assert hits(flat, x, CFG.PAD_INSET)[-1] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("overrides, variant, match", [
    ({"BASE_FRONT_H": 2.0}, "solid", "pocket floor"),
    ({"WINDOW_SIDE_RAIL": 48.0}, "window", "window would be"),
    ({"FOOT_SPACING_X": 82.0}, "frame-solid", "into the frame wall"),
    ({"FOOT_SPACING_X": 82.0}, "solid", "deck edge"),
    ({"POCKET_CHAMFER": 3.0}, "solid", "POCKET_CHAMFER"),
    ({"PAD_INSET": 30.0}, "window", "pad recesses"),
    ({"BASE_ANGLE": 25.0, "BASE_EDGE_MARGIN": 6.0}, "frame-solid", "thinnest frame wall"),
])
def test_invalid_combos_raise(overrides, variant, match):
    """Parameters that break the part raise a ValueError naming the problem.

    Args:
        overrides: Config overrides passed to load_config().
        variant: BASE_VARIANTS key to build.
        match: Regex the ValueError message must match.
    """
    with pytest.raises(ValueError, match=match):
        build_base(load_config(overrides), **VARIANTS[variant])


def test_frame_builds_at_readme_angle():
    """The README's `--angle 12` example still builds the frame variants."""
    cfg = load_config({"BASE_ANGLE": 12.0})
    for name in FRAMED:
        assert build_base(cfg, **VARIANTS[name]).is_watertight
