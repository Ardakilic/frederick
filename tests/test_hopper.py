"""Tests for the single-dose hopper: insert (every variant), capped and open bellows, two-piece body, cap, kits."""

import itertools
import math

import numpy as np
import pytest
import trimesh
from manifold3d import Manifold, Mesh
from shapely.geometry import Point, box
from shapely.ops import unary_union
from trimesh.transformations import translation_matrix

from geometry.common import load_config, revolve
from geometry.hopper import (bellows_open_profile, bellows_profile, build_bellows, build_bellows_open, build_cap,
                             build_insert, build_two_piece_body, insert_profile, kit_poses, two_piece_body_profile)

TESS = 0.02  # mm, radius error of a 128-gon at these sizes is < 0.005
KITS = load_config().HOPPER_KITS
FIXTURES = {"bellows-capped": "bellows", "bellows-open": "bellows_open", "2p-body": "body", "cap": "cap"}  # kit part -> fixture
SCREW_VOLUME = 24399.07364243272  # mm³, the screw insert before screw-reinforced was added (sha256 3f94afb7... STL)
SCREW_TRIANGLES = 14536
# every kit with each insert variant in its insert slot (None: the kit has no insert)
KIT_CASES = [(kit, insert) for kit, parts in KITS.items()
             for insert in (load_config().INSERT_VARIANTS if "insert" in parts else [None])]


@pytest.fixture(scope="module")
def cfg():
    """Default config.

    Returns:
        Config namespace from load_config().
    """
    return load_config()


@pytest.fixture(scope="module")
def inserts(cfg):
    """Every INSERT_VARIANTS entry, built with its flags.

    Args:
        cfg: Default config fixture.

    Returns:
        Dict variant name -> trimesh.Trimesh.
    """
    return {name: build_insert(cfg, **flags) for name, flags in cfg.INSERT_VARIANTS.items()}


@pytest.fixture(scope="module")
def friction(inserts):
    """Insert without the screw hub.

    Args:
        inserts: All insert variants fixture.

    Returns:
        trimesh.Trimesh.
    """
    return inserts["friction"]


@pytest.fixture(scope="module")
def screw(inserts):
    """Insert with the plain screw hub.

    Args:
        inserts: All insert variants fixture.

    Returns:
        trimesh.Trimesh.
    """
    return inserts["screw"]


@pytest.fixture(scope="module")
def screw_reinforced(inserts):
    """Insert with the reinforced screw hub.

    Args:
        inserts: All insert variants fixture.

    Returns:
        trimesh.Trimesh.
    """
    return inserts["screw-reinforced"]


@pytest.fixture(scope="module")
def bellows(cfg):
    """Bellows in print orientation.

    Args:
        cfg: Default config fixture.

    Returns:
        trimesh.Trimesh.
    """
    return build_bellows(cfg)


@pytest.fixture(scope="module")
def bellows_open(cfg):
    """Open bellows in print orientation.

    Args:
        cfg: Default config fixture.

    Returns:
        trimesh.Trimesh.
    """
    return build_bellows_open(cfg)


@pytest.fixture(scope="module")
def body(cfg):
    """Two-piece body in print orientation.

    Args:
        cfg: Default config fixture.

    Returns:
        trimesh.Trimesh.
    """
    return build_two_piece_body(cfg)


@pytest.fixture(scope="module")
def cap(cfg):
    """Cap in print orientation.

    Args:
        cfg: Default config fixture.

    Returns:
        trimesh.Trimesh.
    """
    return build_cap(cfg)


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


@pytest.mark.parametrize("name", ["friction", "screw", "screw_reinforced", "bellows", "bellows_open", "body", "cap"])
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


@pytest.mark.parametrize("name, wall", [("friction", "SPOUT_WALL"), ("screw", "SPOUT_WALL"),
                                        ("body", "TWO_PIECE_WALL")])
def test_spout_diameters(cfg, name, wall, request):
    """Halfway down the spout: OD = THROAT_ID - SPOUT_CLEARANCE, wall = the part's spout wall.

    Args:
        cfg: Default config fixture.
        name: Fixture name of the part under test.
        wall: Config name of that part's spout wall.
        request: pytest request, used to look up the part fixture by name.
    """
    r_min, r_max = section_radii(request.getfixturevalue(name), cfg.THROAT_DEPTH / 2)
    r_so = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2
    assert r_max == pytest.approx(r_so, abs=TESS)
    assert r_min == pytest.approx(r_so - getattr(cfg, wall), abs=TESS)


def kit_ml(cfg, kit):
    """Bean capacity of an assembled kit, nothing counted twice.

    Each part's bean path counts from where the part below stops to its own
    top: the insert and the body from the spout top, the insert only up to
    its ledge (the bellows ring fills the socket), a bellows from its ring or
    cap. The cap only closes the top.

    Args:
        cfg: Config namespace.
        kit: HOPPER_KITS key.

    Returns:
        Capacity in ml.
    """
    profiles = {"insert": insert_profile, "2p-body": two_piece_body_profile,
                "bellows-open": bellows_open_profile, "bellows-capped": bellows_profile}
    ml = 0.0
    for part in cfg.HOPPER_KITS[kit]:
        if part == "cap":
            continue
        wall, void = profiles[part](cfg)
        z0 = cfg.THROAT_DEPTH if part in ("insert", "2p-body") else 0
        z1 = ledge_z(cfg) if part == "insert" else wall.bounds[3]
        ml += revolved_ml(void, z0, z1, cfg.SEGMENTS)
    return ml


@pytest.mark.parametrize("kit, insert", KIT_CASES)
def test_kit_capacity(cfg, kit, insert, inserts):
    """Every kit, assembled with each insert variant, holds a dose: a screw hub stays in the spout, below the
    bean path kit_ml() counts (from THROAT_DEPTH up), so no variant takes capacity away.

    Args:
        cfg: Default config fixture.
        kit: HOPPER_KITS key.
        insert: INSERT_VARIANTS key in the insert slot, or None.
        inserts: All insert variants fixture.
    """
    assert kit_ml(cfg, kit) >= cfg.DOSE_VOLUME_ML
    if insert:
        extra = as_manifold(inserts[insert].vertices, inserts[insert].faces) - as_manifold(
            inserts["friction"].vertices, inserts["friction"].faces)
        assert extra.trim_by_plane((0, 0, 1), cfg.THROAT_DEPTH).volume() < 1e-3   # no hub above the count


def test_two_piece_straight_cone(cfg, body):
    """Halfway up the cone the bean path radius is midway between the spout ID and FUNNEL_TOP_ID.

    Args:
        cfg: Default config fixture.
        body: Two-piece body mesh fixture.
    """
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.TWO_PIECE_WALL
    z_mid = cfg.THROAT_DEPTH + cfg.TWO_PIECE_WALL + cfg.TWO_PIECE_FUNNEL_H / 2
    assert section_radii(body, z_mid)[0] == pytest.approx((r_si + cfg.FUNNEL_TOP_ID / 2) / 2, abs=0.2)


def test_cap_diameters(cfg, cap):
    """Disc OD = BELLOWS_OD + 2 CAP_LIP; plug OD = collar ID - CAP_FIT_CLEARANCE, wall CAP_PLUG_WALL.

    Args:
        cfg: Default config fixture.
        cap: Two-piece cap mesh fixture.
    """
    assert section_radii(cap, cfg.CAP_T / 2)[1] == pytest.approx(cfg.BELLOWS_OD / 2 + cfg.CAP_LIP, abs=TESS)
    r_min, r_max = section_radii(cap, cfg.CAP_T + cfg.CAP_PLUG_H / 2)
    r_po = (cfg.BELLOWS_OD - 2 * cfg.BELLOWS_RING_WALL - cfg.CAP_FIT_CLEARANCE) / 2
    assert r_max == pytest.approx(r_po, abs=TESS)
    assert r_min == pytest.approx(r_po - cfg.CAP_PLUG_WALL, abs=TESS)


@pytest.mark.parametrize("name", ["body", "bellows_open"])
def test_cap_fits_collar(cfg, name, cap, request):
    """Both collar parts end in the same collar: BELLOWS_OD outside, BELLOWS_RING_WALL thick, CAP_COLLAR_H of
    straight bore; the one cap's plug is narrower than that bore and no taller.

    Args:
        cfg: Default config fixture.
        name: Fixture name of the two-piece body or the open bellows.
        cap: Cap mesh fixture.
        request: pytest request, used to look up the part fixture by name.
    """
    part = request.getfixturevalue(name)
    top = part.bounds[1][2]
    bore, outer = section_radii(part, top - cfg.CAP_COLLAR_H / 2)
    assert outer == pytest.approx(cfg.BELLOWS_OD / 2, abs=TESS)
    assert bore == pytest.approx(cfg.BELLOWS_OD / 2 - cfg.BELLOWS_RING_WALL, abs=TESS)
    assert section_radii(part, top - cfg.CAP_COLLAR_H + 0.01)[0] == pytest.approx(bore, abs=TESS)
    assert section_radii(cap, cfg.CAP_T + 0.01)[1] < bore
    assert cap.extents[2] - cfg.CAP_T <= cfg.CAP_COLLAR_H


@pytest.mark.parametrize("name, floor", [("bellows", "BELLOWS_CAP_T"), ("bellows_open", None)])
def test_bellows_bean_path(cfg, name, floor, request):
    """The narrowest bore of each bellows (above the cap, if any) is at most 6 mm under the funnel top ID.

    Args:
        cfg: Default config fixture.
        name: Fixture name of the bellows under test.
        floor: Config name of the cap thickness to skip, or None.
        request: pytest request, used to look up the part fixture by name.
    """
    v = request.getfixturevalue(name).vertices
    r = np.hypot(v[:, 0], v[:, 1])[v[:, 2] > (getattr(cfg, floor) if floor else 0) + 1e-6]
    assert 2 * r.min() >= cfg.FUNNEL_TOP_ID - 6


@pytest.mark.parametrize("name, at_top", [("bellows", True), ("bellows_open", False)])
def test_bellows_fits_socket(cfg, name, at_top, request):
    """Ring OD = SOCKET_ID - BELLOWS_FIT_CLEARANCE, wall BELLOWS_RING_WALL, no deeper than the socket;
    the capped bellows has it on top, the open one on the bed.

    Args:
        cfg: Default config fixture.
        name: Fixture name of the bellows under test.
        at_top: The ring is at the top of the print (else at the bottom).
        request: pytest request, used to look up the part fixture by name.
    """
    mesh = request.getfixturevalue(name)
    z = mesh.bounds[1][2] - cfg.BELLOWS_RING_H / 2 if at_top else cfg.BELLOWS_RING_H / 2
    r_min, r_max = section_radii(mesh, z)
    r_ro = (cfg.SOCKET_ID - cfg.BELLOWS_FIT_CLEARANCE) / 2
    assert r_max == pytest.approx(r_ro, abs=TESS)
    assert r_min == pytest.approx(r_ro - cfg.BELLOWS_RING_WALL, abs=TESS)
    assert cfg.BELLOWS_RING_H <= cfg.SOCKET_DEPTH


def test_bellows_open_ends(cfg, bellows_open):
    """Open at both ends: a ray down the axis passes; its height is ring + flank + folds + collar.

    Args:
        cfg: Default config fixture.
        bellows_open: Open bellows mesh fixture.
    """
    assert len(hits_z(bellows_open, [(0, 0, -1)], (0, 0, 1))) == 0
    r_out = cfg.BELLOWS_OD / 2
    k = cfg.BELLOWS_FOLD_PITCH / 2 / cfg.BELLOWS_FOLD_DEPTH
    flank = (r_out - (cfg.SOCKET_ID - cfg.BELLOWS_FIT_CLEARANCE) / 2) * k
    height = (cfg.BELLOWS_RING_H + flank + cfg.BELLOWS_FOLDS * cfg.BELLOWS_FOLD_PITCH
              + cfg.BELLOWS_RING_WALL + cfg.CAP_COLLAR_H)
    assert bellows_open.extents[2] == pytest.approx(height)


def test_kit_pose_keys(cfg):
    """One pose per part of every kit; the part in the throat keeps identity, the others are rigid motions.

    Args:
        cfg: Default config fixture.
    """
    poses = kit_poses(cfg)
    assert list(poses) == list(cfg.HOPPER_KITS)
    for kit, parts in cfg.HOPPER_KITS.items():
        assert list(poses[kit]) == parts
        assert np.array_equal(poses[kit][parts[0]], np.eye(4))
        for pose in poses[kit].values():
            assert pose.shape == (4, 4) and np.linalg.det(pose[:3, :3]) == pytest.approx(1)
    assert np.array_equal(poses["3-part"]["bellows-open"][:3, :3], np.eye(3))   # ring down, not flipped
    assert poses["3-part"]["bellows-open"][2, 3] == pytest.approx(ledge_z(cfg))


@pytest.mark.parametrize("kit, insert", KIT_CASES)
def test_kit_fits(cfg, kit, insert, request):
    """In kit pose no two parts cut into each other, and each part touches the one below: 0.5 mm lower, they overlap.

    Args:
        cfg: Default config fixture.
        kit: HOPPER_KITS key.
        insert: INSERT_VARIANTS key in the insert slot, or None.
        request: pytest request, used to look up the part fixtures by name.
    """
    poses = kit_poses(cfg)[kit]

    def placed(part, dz=0.0):
        """The named kit part in the hopper frame, lowered by dz.

        Args:
            part: Part name as in HOPPER_KITS.
            dz: Extra drop (mm).

        Returns:
            manifold3d.Manifold.
        """
        mesh = request.getfixturevalue("inserts")[insert] if part == "insert" else request.getfixturevalue(FIXTURES[part])
        solid = as_manifold(trimesh.transform_points(mesh.vertices, poses[part]) - (0, 0, dz), mesh.faces)
        assert solid.volume() == pytest.approx(mesh.volume, rel=1e-4)   # a rigid pose keeps it closed and outward
        return solid

    parts = cfg.HOPPER_KITS[kit]
    for a, b in itertools.combinations(parts, 2):
        assert (placed(a) ^ placed(b)).volume() < 1e-3
    for below, upper in zip(parts, parts[1:]):
        assert (placed(below) ^ placed(upper, 0.5)).volume() > 1


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


def spoke_area(mesh, z, r0, r1):
    """Material area of the horizontal section at z between radii r0 and r1 (the spokes, inside a spout).

    Args:
        mesh: trimesh.Trimesh.
        z: Section height (mm).
        r0: Inner radius of the annulus measured (mm).
        r1: Outer radius (mm).

    Returns:
        Area in mm².
    """
    path, _ = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1)).to_2D(
        to_2D=translation_matrix((0, 0, -z)))
    annulus = Point(0, 0).buffer(r1).difference(Point(0, 0).buffer(r0))
    return unary_union(path.polygons_full).intersection(annulus).area


def test_strong_hub(cfg, screw_reinforced):
    """Reinforced hub: the axis ray goes through the hole, the washer seat is flat at STRONG_HUB_H with no spoke
    over it, the rim outside it is a 45° cone, and a ray down onto a spoke lands on its 45° roof (ridge at
    STRONG_HUB_H + STRONG_SPOKE_W / 2, on full-height sides).

    Args:
        cfg: Default config fixture.
        screw_reinforced: Reinforced screw insert mesh fixture.
    """
    mesh, h = screw_reinforced, cfg.STRONG_HUB_H
    assert len(hits_z(mesh, [(0, 0, -1)], (0, 0, 1))) == 0
    r_seat = (cfg.WASHER_D + cfg.WASHER_CLEARANCE) / 2
    between = math.pi / cfg.SPOKES  # angle halfway between two spokes

    def down(r, a):
        """Highest hit of a ray straight down at radius r, angle a.

        Args:
            r: Radius (mm).
            a: Angle from +X (rad).

        Returns:
            z in mm.
        """
        return hits_z(mesh, [(r * math.cos(a), r * math.sin(a), 200)], (0, 0, -1)).max()

    for r in np.linspace(cfg.SCREW_HOLE_D / 2 + 0.1, r_seat - 0.1, 4):
        for a in np.linspace(0, 2 * math.pi, 7)[:-1] + 0.1:
            assert down(r, a) == pytest.approx(h)
    for r in np.linspace(r_seat + 0.1, cfg.STRONG_HUB_OD / 2 - 0.1, 4):
        assert down(r, between) == pytest.approx(h - (r - r_seat), abs=TESS)
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.SPOUT_WALL
    on_spoke = ((cfg.STRONG_HUB_OD / 2 + r_si) / 2, cfg.STRONG_SPOKE_W / 4, 200)
    assert hits_z(mesh, [on_spoke], (0, 0, -1)).max() == pytest.approx(h + cfg.STRONG_SPOKE_W / 4)
    assert section_radii(mesh, h + 0.01)[0] > r_seat   # above the seat level nothing reaches over the seat


def test_strong_spokes_wider(cfg, screw, screw_reinforced):
    """At mid hub height the reinforced spokes have more section area than the plain ones, by the width ratio.

    Args:
        cfg: Default config fixture.
        screw: Screw insert mesh fixture.
        screw_reinforced: Reinforced screw insert mesh fixture.
    """
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.SPOUT_WALL
    z = min(cfg.HUB_H, cfg.STRONG_HUB_H) / 2
    r0, r1 = max(cfg.HUB_OD, cfg.STRONG_HUB_OD) / 2 + 0.5, r_si - 0.5
    plain, strong = (spoke_area(m, z, r0, r1) for m in (screw, screw_reinforced))
    assert plain == pytest.approx(cfg.SPOKES * cfg.SPOKE_W * (r1 - r0), rel=0.02)
    assert strong == pytest.approx(cfg.SPOKES * cfg.STRONG_SPOKE_W * (r1 - r0), rel=0.02)
    assert strong > plain


def bending_i(poly):
    """Second moment of area of a section about its horizontal centroid axis (bending under a vertical load).

    Args:
        poly: shapely Polygon in (y, z), no holes.

    Returns:
        I in mm⁴.
    """
    y, z = np.asarray(poly.exterior.coords).T
    cross = y[:-1] * z[1:] - y[1:] * z[:-1]
    return abs(np.sum(cross * (z[:-1] ** 2 + z[:-1] * z[1:] + z[1:] ** 2))) / 12 - poly.area * poly.centroid.y ** 2


def test_strong_spokes_stiffer(cfg, screw, screw_reinforced):
    """Across a spoke at mid-span (vertical section) the reinforced spoke has more area and at least twice the
    plain spoke's bending stiffness (second moment of area); the plain one measures SPOKE_W x HUB_H.

    Args:
        cfg: Default config fixture.
        screw: Screw insert mesh fixture.
        screw_reinforced: Reinforced screw insert mesh fixture.
    """
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.SPOUT_WALL
    x = (cfg.STRONG_HUB_OD / 2 + r_si) / 2
    to_plane = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -x], [0, 0, 0, 1]], dtype=float)  # (y, z) of plane x
    keep = box(-cfg.STRONG_SPOKE_W, -1, cfg.STRONG_SPOKE_W, cfg.THROAT_DEPTH)  # the spoke on +X, not the spout wall

    def spoke(mesh):
        """The +X spoke's cross-section at mid-span.

        Args:
            mesh: Insert mesh.

        Returns:
            shapely Polygon in (y, z).
        """
        path, _ = mesh.section(plane_origin=(x, 0, 0), plane_normal=(1, 0, 0)).to_2D(to_2D=to_plane)
        return unary_union(path.polygons_full).intersection(keep)

    plain, strong = spoke(screw), spoke(screw_reinforced)
    assert bending_i(plain) == pytest.approx(cfg.SPOKE_W * cfg.HUB_H ** 3 / 12, rel=1e-6)
    assert strong.area > plain.area
    assert bending_i(strong) >= 2 * bending_i(plain)


def test_screw_unchanged(screw):
    """Adding screw-reinforced left the plain screw insert as it was (volume and triangle count).

    Args:
        screw: Screw insert mesh fixture.
    """
    assert screw.volume == pytest.approx(SCREW_VOLUME, rel=1e-9)
    assert len(screw.faces) == SCREW_TRIANGLES


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


@pytest.mark.parametrize("profile, wall_name, height_name", [
    (insert_profile, "INSERT_WALL", "FUNNEL_H"),
    (two_piece_body_profile, "TWO_PIECE_WALL", "TWO_PIECE_FUNNEL_H"),
])
def test_funnel_wall(cfg, profile, wall_name, height_name):
    """From the spout-to-funnel corner to the funnel top the bean path has >= 0.9 wall outside it.

    Args:
        cfg: Default config fixture.
        profile: Profile function returning (wall, void).
        wall_name: Config name of the funnel wall thickness.
        height_name: Config name of the funnel height.
    """
    t = getattr(cfg, wall_name)
    wall, void = profile(cfg)
    outside = wall.exterior.difference(void.buffer(1e-6))
    z0 = cfg.THROAT_DEPTH + t
    z1 = z0 + getattr(cfg, height_name)
    path = [Point(p) for p in void.exterior.segmentize(0.5).coords if z0 - 1e-9 <= p[1] <= z1 + 1e-9 and p[0] > 0]
    assert min(outside.distance(p) for p in path) >= 0.9 * t


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


@pytest.mark.parametrize("build", [build_bellows, build_bellows_open])
def test_folds_set_bellows_height(cfg, build):
    """Each extra fold adds one pitch of height, to the capped and the open bellows.

    Args:
        cfg: Default config fixture.
        build: Bellows builder.
    """
    low = build(load_config({"BELLOWS_FOLDS": 2})).extents[2]
    high = build(load_config({"BELLOWS_FOLDS": 5})).extents[2]
    assert high - low == pytest.approx(3 * cfg.BELLOWS_FOLD_PITCH)


def test_folds_set_body_height(cfg):
    """Each extra fold adds one pitch to the two-piece body, and the cap pose follows in both cap kits.

    Args:
        cfg: Default config fixture.
    """
    low, high = (load_config({"BELLOWS_FOLDS": n}) for n in (2, 5))
    assert build_two_piece_body(high).extents[2] - build_two_piece_body(low).extents[2] == pytest.approx(
        3 * cfg.BELLOWS_FOLD_PITCH)
    for kit in ("two-piece", "3-part"):
        lift = kit_poses(high)[kit]["cap"][2, 3] - kit_poses(low)[kit]["cap"][2, 3]
        assert lift == pytest.approx(3 * cfg.BELLOWS_FOLD_PITCH)


@pytest.mark.parametrize("overrides, build, match", [
    ({"HUB_OD": 31.0}, "screw", "HUB_OD"),                         # hub wider than the spout bore
    ({"SPOKES": 11}, "strong", "block the bean path"),             # 11 x 4.5 > half of 30.4 pi
    ({"STRONG_HUB_OD": 27.0}, "strong", "spout ID - 4"),           # hub crowds the spout bore
    ({"WASHER_D": 12.0}, "strong", "cone rim"),                    # seat as wide as the hub
    ({"WASHER_D": 3.5}, "strong", "cover the hole"),               # washer narrower than the hole
    ({"STRONG_HUB_H": 18.0}, "strong", "spoke ridge"),             # ridge 20.25 above the spout top
    ({"STRONG_HUB_H": 1.0}, "strong", "above the cone"),           # cone 1.25 tall
    ({"STRONG_SPOKE_W": 8.0}, "strong", "reach into the hub"),     # corners outside the hub at the seat edge
    ({"FUNNEL_TOP_ID": 66.0}, "insert", "SOCKET_ID"),              # no ledge for the bellows
    ({"FUNNEL_H": 15.0}, "insert", "bottom tangent"),              # 87° bulb bottom, needs support
    ({"INSERT_WALL": 5.0}, "insert", "INSERT_WALL"),               # bulb wider than the socket
    ({"SHOULDER_OD": 35.0}, "insert", "SHOULDER_OD"),              # stop narrower than spout OD + 2
    ({"SHOULDER_OD": 71.0}, "insert", "SHOULDER_OD"),              # stop wider than the socket OD
    ({"BELLOWS_FOLD_PITCH": 9.0}, "bellows", "flank"),             # 50° flanks need support
    ({"BELLOWS_RING_H": 9.0}, "bellows", "SOCKET_DEPTH"),          # ring deeper than the socket
    ({"SOCKET_ID": 72.0}, "bellows", "fold peaks"),               # ring wider than the folds
    ({"BELLOWS_FOLD_PITCH": 9.0}, "open", "flank"),                # 50° flanks need support
    ({"BELLOWS_RING_H": 9.0}, "open", "SOCKET_DEPTH"),             # ring deeper than the socket
    ({"SOCKET_ID": 72.0}, "open", "fold peaks"),                   # ring wider than the folds
    ({"TWO_PIECE_FUNNEL_H": 15.0}, "body", "half-angle"),          # 47° cone, needs support
    ({"BELLOWS_FOLD_PITCH": 9.0}, "body", "flank"),                # 50° flanks need support
    ({"CAP_PLUG_H": 7.0}, "cap", "CAP_COLLAR_H"),                  # plug taller than the collar
    ({"CAP_PLUG_WALL": 33.0}, "cap", "bore"),                      # plug wall fills the plug
    ({"HOPPER_KITS": {"x": ["cap", "insert"]}}, "kits", "must start"),         # no part in the throat
    ({"HOPPER_KITS": {"x": ["insert", "lid"]}}, "kits", "'lid' cannot sit"),   # unknown part
    ({"HOPPER_KITS": {"x": ["insert", "cap", "cap"]}}, "kits", "on 'cap'"),    # nothing sits on a cap
])
def test_invalid_params(overrides, build, match):
    """Inconsistent hopper parameters raise ValueError naming the problem.

    Args:
        overrides: Config overrides passed to load_config().
        build: Builder to call: insert, screw, strong (screw-reinforced), bellows, open, body, cap or kits
            (kit_poses).
        match: Regex the ValueError message must match.
    """
    cfg = load_config(overrides)
    builders = {"insert": lambda: build_insert(cfg, screw_hub=False),
                "screw": lambda: build_insert(cfg, screw_hub=True),
                "strong": lambda: build_insert(cfg, screw_hub=True, reinforced=True),
                "bellows": lambda: build_bellows(cfg),
                "open": lambda: build_bellows_open(cfg),
                "body": lambda: build_two_piece_body(cfg),
                "cap": lambda: build_cap(cfg),
                "kits": lambda: kit_poses(cfg)}
    with pytest.raises(ValueError, match=match):
        builders[build]()
