"""Tests for the single-dose hopper: insert (both variants) and bellows."""

import math

import numpy as np
import pytest
from manifold3d import Manifold, Mesh
from shapely.geometry import Point, box

from geometry.common import load_config, revolve
from geometry.hopper import bellows_profile, build_bellows, build_insert, insert_profile

TESS = 0.02  # mm, radius error of a 128-gon at these sizes is < 0.005


@pytest.fixture(scope="module")
def cfg():
    """Default config.

    Returns:
        Config namespace from load_config().
    """
    return load_config()


@pytest.fixture(scope="module")
def friction(cfg):
    """Insert without the screw hub.

    Args:
        cfg: Default config fixture.

    Returns:
        trimesh.Trimesh.
    """
    return build_insert(cfg, screw_hub=False)


@pytest.fixture(scope="module")
def screw(cfg):
    """Insert with the screw hub.

    Args:
        cfg: Default config fixture.

    Returns:
        trimesh.Trimesh.
    """
    return build_insert(cfg, screw_hub=True)


@pytest.fixture(scope="module")
def bellows(cfg):
    """Bellows in print orientation.

    Args:
        cfg: Default config fixture.

    Returns:
        trimesh.Trimesh.
    """
    return build_bellows(cfg)


def section_radii(mesh, z):
    """Smallest and largest radius of the horizontal section at height z.

    Args:
        mesh: trimesh.Trimesh.
        z: Section height (mm).

    Returns:
        (r_min, r_max) in mm.
    """
    xy = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1)).vertices[:, :2]
    r = np.hypot(xy[:, 0], xy[:, 1])
    return r.min(), r.max()


def ledge_z(cfg):
    """Height of the ledge the bellows rests on: the bulb starts INSERT_WALL above the spout top.

    Args:
        cfg: Config namespace.

    Returns:
        z in mm.
    """
    return cfg.THROAT_DEPTH + cfg.INSERT_WALL + cfg.FUNNEL_H


def revolved_ml(profile, z0, z1, segments):
    """Volume of the part of an (r, z) profile between z0 and z1, revolved.

    Args:
        profile: shapely Polygon in the (r, z) half-plane.
        z0: Lower cut (mm).
        z1: Upper cut (mm).
        segments: Circle resolution.

    Returns:
        Volume in ml.
    """
    part = profile.intersection(box(0, z0, 1e3, z1))
    return sum(revolve(g, segments).volume() for g in getattr(part, "geoms", [part]) if g.area > 0) / 1000


def hits_z(mesh, origins, direction):
    """z of every place the rays hit the mesh.

    Args:
        mesh: trimesh.Trimesh.
        origins: (n, 3) ray origins.
        direction: One (3,) direction shared by all rays.

    Returns:
        numpy array of hit z values (empty if nothing is hit).
    """
    origins = np.asarray(origins, dtype=float)
    locations, _, _ = mesh.ray.intersects_location(origins, np.tile(direction, (len(origins), 1)))
    return np.reshape(locations, (-1, 3))[:, 2]


def as_manifold(vertices, faces):
    """Wrap a triangle mesh as a manifold3d solid for booleans.

    Args:
        vertices: (n, 3) vertex positions.
        faces: (m, 3) vertex indices.

    Returns:
        manifold3d.Manifold.
    """
    return Manifold(Mesh(vert_properties=np.ascontiguousarray(vertices, dtype=np.float32),
                         tri_verts=np.ascontiguousarray(faces, dtype=np.uint32)))


@pytest.mark.parametrize("name", ["friction", "screw", "bellows"])
def test_printable_solid(name, request):
    """Watertight, one body, positive volume, on the bed, no overhang over 45° above the bed.

    Args:
        name: Fixture name of the part under test.
        request: pytest request, used to look up the part fixture by name.
    """
    mesh = request.getfixturevalue(name)
    assert mesh.is_watertight
    assert mesh.body_count == 1
    assert mesh.volume > 0
    assert mesh.bounds[0][2] == pytest.approx(0, abs=1e-6)
    down = mesh.face_normals[:, 2] < -math.cos(math.radians(45)) - 1e-6
    on_bed = mesh.triangles[:, :, 2].max(axis=1) < 1e-6
    assert not np.any(down & ~on_bed)


@pytest.mark.parametrize("name", ["friction", "screw"])
def test_spout_diameters(cfg, name, request):
    """Halfway down the spout: OD = THROAT_ID - SPOUT_CLEARANCE, wall SPOUT_WALL.

    Args:
        cfg: Default config fixture.
        name: Fixture name of the part under test.
        request: pytest request, used to look up the part fixture by name.
    """
    r_min, r_max = section_radii(request.getfixturevalue(name), cfg.THROAT_DEPTH / 2)
    r_so = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2
    assert r_max == pytest.approx(r_so, abs=TESS)
    assert r_min == pytest.approx(r_so - cfg.SPOUT_WALL, abs=TESS)


def test_capacity(cfg, bellows):
    """Funnel (spout top to ledge) plus the bellows cavity holds a dose; nothing is counted twice.

    Args:
        cfg: Default config fixture.
        bellows: Bellows mesh fixture.
    """
    _, insert_void = insert_profile(cfg)
    _, bellows_void = bellows_profile(cfg)
    funnel = revolved_ml(insert_void, cfg.THROAT_DEPTH, ledge_z(cfg), cfg.SEGMENTS)
    cavity = revolved_ml(bellows_void, 0, bellows.bounds[1][2], cfg.SEGMENTS)
    assert funnel + cavity >= cfg.DOSE_VOLUME_ML


def test_bellows_bean_path(cfg, bellows):
    """The narrowest bore of the bellows is at most 6 mm under the funnel top ID.

    Args:
        cfg: Default config fixture.
        bellows: Bellows mesh fixture.
    """
    v = bellows.vertices
    r = np.hypot(v[:, 0], v[:, 1])[v[:, 2] > cfg.BELLOWS_CAP_T + 1e-6]
    assert 2 * r.min() >= cfg.FUNNEL_TOP_ID - 6


def test_bellows_fits_socket(cfg, friction, bellows):
    """Ring OD and height fit the socket; seated on the ledge, the bellows does not touch the insert.

    Args:
        cfg: Default config fixture.
        friction: Friction insert mesh fixture.
        bellows: Bellows mesh fixture.
    """
    top = bellows.bounds[1][2]
    assert section_radii(bellows, top - cfg.BELLOWS_RING_H / 2)[1] == pytest.approx(
        (cfg.SOCKET_ID - cfg.BELLOWS_FIT_CLEARANCE) / 2, abs=TESS)
    assert cfg.BELLOWS_RING_H <= cfg.SOCKET_DEPTH
    ledge = ledge_z(cfg)
    flipped = bellows.vertices * (1, -1, -1) + (0, 0, ledge + top)  # 180° about X, ring end on the ledge
    seated = as_manifold(flipped, bellows.faces)
    assert seated.volume() == pytest.approx(bellows.volume, rel=1e-4)
    assert (seated ^ as_manifold(friction.vertices, friction.faces)).volume() < 1e-3


def test_screw_hub(cfg, screw):
    """The axis ray goes through the screw hole; a ray down onto a spoke lands at HUB_H.

    Args:
        cfg: Default config fixture.
        screw: Screw insert mesh fixture.
    """
    assert len(hits_z(screw, [(0, 0, -1)], (0, 0, 1))) == 0
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.SPOUT_WALL
    on_spoke = ((cfg.HUB_OD / 2 + r_si) / 2, cfg.SPOKE_W / 4, 200)
    assert hits_z(screw, [on_spoke], (0, 0, -1)).max() == pytest.approx(cfg.HUB_H)


def test_friction_open_near_axis(cfg, friction):
    """Without the hub nothing sits below HUB_H inside the spout bore.

    Args:
        cfg: Default config fixture.
        friction: Friction insert mesh fixture.
    """
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.SPOUT_WALL
    rays = [(r, 0.1, -1) for r in np.linspace(0, r_si - 0.5, 8)]
    z = hits_z(friction, rays, (0, 0, 1))
    assert not np.any(z < cfg.HUB_H)


def test_bulb_is_convex(cfg, friction):
    """Halfway up the bulb the bean path is wider than a straight cone would be.

    Args:
        cfg: Default config fixture.
        friction: Friction insert mesh fixture.
    """
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.SPOUT_WALL
    r_min = section_radii(friction, ledge_z(cfg) - cfg.FUNNEL_H / 2)[0]
    assert r_min > (r_si + cfg.FUNNEL_TOP_ID / 2) / 2 + 1


def test_bulb_bottom_tangent(cfg, friction):
    """No upward face below the ledge is flatter than 45° from vertical, the bulb's bottom included.

    Args:
        cfg: Default config fixture.
        friction: Friction insert mesh fixture.
    """
    up = friction.face_normals[:, 2] > math.cos(math.radians(45)) + 1e-6
    below_ledge = friction.triangles[:, :, 2].max(axis=1) < ledge_z(cfg) - 1e-6
    assert not np.any(up & below_ledge)


def test_bulb_wall(cfg):
    """From the bulb's bottom corner to the ledge the bean path has >= 0.9 INSERT_WALL of wall outside it.

    Args:
        cfg: Default config fixture.
    """
    wall, void = insert_profile(cfg)
    outside = wall.exterior.difference(void.buffer(1e-6))
    z0 = cfg.THROAT_DEPTH + cfg.INSERT_WALL
    path = [Point(p) for p in void.exterior.coords if z0 - 1e-9 <= p[1] <= ledge_z(cfg) and p[0] > 0]
    assert min(outside.distance(p) for p in path) >= 0.9 * cfg.INSERT_WALL


@pytest.mark.parametrize("overrides", [{}, {"SHOULDER_OD": 50.0}])
def test_seating_shoulder(overrides):
    """The 45° step runs out to SHOULDER_OD and the collar shows just above it; the override moves it.

    Args:
        overrides: Config overrides passed to load_config().
    """
    cfg = load_config(overrides)
    insert = build_insert(cfg, screw_hub=False)
    r_sh = cfg.SHOULDER_OD / 2
    z_sh = cfg.THROAT_DEPTH + r_sh - (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2
    assert section_radii(insert, z_sh - 0.5)[1] == pytest.approx(r_sh - 0.5, abs=TESS)
    assert section_radii(insert, z_sh + 0.5)[1] == pytest.approx(r_sh, abs=TESS)


def test_throat_id_moves_spout():
    """THROAT_ID drives the spout OD."""
    cfg = load_config({"THROAT_ID": 35.0})
    r_max = section_radii(build_insert(cfg, screw_hub=False), cfg.THROAT_DEPTH / 2)[1]
    assert r_max == pytest.approx((35.0 - cfg.SPOUT_CLEARANCE) / 2, abs=TESS)


def test_folds_set_bellows_height(cfg):
    """Each extra fold adds one pitch of height.

    Args:
        cfg: Default config fixture.
    """
    low = build_bellows(load_config({"BELLOWS_FOLDS": 2})).extents[2]
    high = build_bellows(load_config({"BELLOWS_FOLDS": 5})).extents[2]
    assert high - low == pytest.approx(3 * cfg.BELLOWS_FOLD_PITCH)


@pytest.mark.parametrize("overrides, build, match", [
    ({"HUB_OD": 31.0}, "screw", "HUB_OD"),                         # hub wider than the spout bore
    ({"FUNNEL_TOP_ID": 66.0}, "insert", "SOCKET_ID"),              # no ledge for the bellows
    ({"FUNNEL_H": 15.0}, "insert", "bottom tangent"),              # 87° bulb bottom, needs support
    ({"INSERT_WALL": 5.0}, "insert", "INSERT_WALL"),               # bulb wider than the socket
    ({"SHOULDER_OD": 35.0}, "insert", "SHOULDER_OD"),              # stop narrower than spout OD + 2
    ({"SHOULDER_OD": 71.0}, "insert", "SHOULDER_OD"),              # stop wider than the socket OD
    ({"BELLOWS_FOLD_PITCH": 9.0}, "bellows", "flank"),             # 50° flanks need support
    ({"BELLOWS_RING_H": 9.0}, "bellows", "SOCKET_DEPTH"),          # ring deeper than the socket
    ({"SOCKET_ID": 72.0}, "bellows", "fold peaks"),               # ring wider than the folds
])
def test_invalid_params(overrides, build, match):
    """Inconsistent hopper parameters raise ValueError naming the problem.

    Args:
        overrides: Config overrides passed to load_config().
        build: Builder to call: insert, screw or bellows.
        match: Regex the ValueError message must match.
    """
    cfg = load_config(overrides)
    builders = {"insert": lambda: build_insert(cfg, screw_hub=False),
                "screw": lambda: build_insert(cfg, screw_hub=True),
                "bellows": lambda: build_bellows(cfg)}
    with pytest.raises(ValueError, match=match):
        builders[build]()
