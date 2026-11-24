"""Single-dose hopper: a printed insert for the grinder throat and a TPU bellows.

Both parts are solids of revolution. Each (r, z) profile is an outer envelope
minus a void, so every wall comes from the same few lines. Print orientation:
insert spout down, bellows cap down, z=0 on the bed.
"""

import math

import numpy as np
from shapely.affinity import rotate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from geometry.common import prism, revolve, to_trimesh

MAX_OVERHANG = 45.0  # deg from vertical that FDM prints without support


def _check(checks):
    """Raise one ValueError listing every failed check.

    Args:
        checks: Iterable of (ok, message) pairs.

    Raises:
        ValueError: At least one ok is false.
    """
    errors = [msg for ok, msg in checks if not ok]
    if errors:
        raise ValueError("hopper config error:\n  " + "\n  ".join(errors))


def insert_profile(cfg):
    """(r, z) profile of the insert: spout, 45° seating shoulder, bulb, socket.

    The bean path is the spout bore, carried INSERT_WALL past THROAT_DEPTH so
    the corner keeps a full wall, then a circular arc out to FUNNEL_TOP_ID,
    vertical at the top: a convex bulb, flattest at the bottom. The wall is
    that arc thickened by INSERT_WALL. Outside, bottom up: the
    spout, 45° out to SHOULDER_OD, then the collar or the bulb, whichever is
    larger, then 45° out to the socket; nothing leans out past 45°.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        (wall, void): shapely Polygons. wall is the part's profile; void is
        the bean path, from below the spout to above the socket mouth.

    Raises:
        ValueError: The bulb's bottom tangent is flatter than 45°, there is no
            ledge for the bellows, the shoulder is out of range, or the bulb
            is wider than the socket.
    """
    r_so = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2
    r_si = r_so - cfg.SPOUT_WALL
    r_sh = cfg.SHOULDER_OD / 2
    r_ft = cfg.FUNNEL_TOP_ID / 2
    r_ki = cfg.SOCKET_ID / 2
    r_ko = r_ki + cfg.SOCKET_WALL
    dr, h = r_ft - r_si, cfg.FUNNEL_H
    z_t = cfg.THROAT_DEPTH
    z_f = z_t + cfg.INSERT_WALL + h  # ledge; the bulb starts INSERT_WALL above the spout top
    z_k = z_f - cfg.SOCKET_WALL  # underside of the socket
    z_top = z_f + cfg.SOCKET_DEPTH
    tangent = 2 * math.degrees(math.atan2(dr, h))  # bottom tangent from vertical, = asin(h / R)
    _check([
        (0 < tangent <= MAX_OVERHANG,
         f"bulb bottom tangent {tangent:.1f}° from vertical must be in (0, {MAX_OVERHANG:g}] (it prints "
         "spout down): FUNNEL_TOP_ID must exceed the spout ID; use a larger FUNNEL_H or a smaller FUNNEL_TOP_ID"),
        (cfg.FUNNEL_TOP_ID < cfg.SOCKET_ID, "FUNNEL_TOP_ID must be < SOCKET_ID (the ledge the bellows rests on)"),
        (2 * r_so + 2 < cfg.SHOULDER_OD < 2 * r_ko,
         "SHOULDER_OD must be > spout OD + 2 and < SOCKET_ID + 2 * SOCKET_WALL"),
        (0 < cfg.INSERT_WALL <= r_ko - r_ft,
         "need 0 < INSERT_WALL <= (SOCKET_ID + 2 * SOCKET_WALL - FUNNEL_TOP_ID) / 2: the bulb must fit under the socket"),
    ])
    big_r = (dr ** 2 + h ** 2) / (2 * dr)  # arc centre (r_ft - big_r, z_f)
    phi = math.asin(h / big_r)  # arc angle = bottom tangent
    a = np.linspace(-phi, 0, math.ceil(cfg.SEGMENTS * phi / (2 * math.pi)) + 1)  # circles' angular step
    arc = np.column_stack([r_ft - big_r * (1 - np.cos(a)), z_f + big_r * np.sin(a)])
    collar = Polygon([(0, 0), (r_so, 0), (r_so, z_t), (r_sh, z_t + r_sh - r_so), (r_sh, z_top), (0, z_top)])
    socket = Polygon([(0, z_k - r_ko), (r_ko, z_k), (r_ko, z_top), (0, z_top)])
    bulb = LineString(arc).buffer(cfg.INSERT_WALL, quad_segs=cfg.SEGMENTS // 4)
    # spout, then nothing further out than 45° from its top edge: no overhang
    clip = Polygon([(0, 0), (r_so, 0), (r_so, z_t), (r_so + z_top, z_t + z_top), (0, z_t + z_top)])
    envelope = unary_union([collar, socket, bulb]).intersection(clip)
    void = Polygon([(0, -1), (r_si, -1), *arc, (r_ki, z_f), (r_ki, z_top + 1), (0, z_top + 1)])
    return envelope.difference(void), void


def _hub_plan(cfg):
    """Plan view of the screw hub and its spokes, z 0..HUB_H.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        shapely Polygon: hub ring plus SPOKES radial spokes reaching into the spout wall.

    Raises:
        ValueError: The hub does not fit in the spout or has no material around the hole.
    """
    r_si = (cfg.THROAT_ID - cfg.SPOUT_CLEARANCE) / 2 - cfg.SPOUT_WALL
    _check([
        (cfg.SCREW_HOLE_D < cfg.HUB_OD < 2 * r_si, "need SCREW_HOLE_D < HUB_OD < spout ID"),
        (0 < cfg.HUB_H <= cfg.THROAT_DEPTH, "HUB_H must be in (0, THROAT_DEPTH]"),
        (cfg.SPOKES >= 1 and cfg.SPOKE_W > 0, "need SPOKES >= 1 and SPOKE_W > 0"),
    ])
    quad = cfg.SEGMENTS // 4
    spoke = box(0, -cfg.SPOKE_W / 2, r_si + cfg.SPOUT_WALL / 2, cfg.SPOKE_W / 2)  # ends inside the wall
    plan = unary_union([Point(0, 0).buffer(cfg.HUB_OD / 2, quad_segs=quad)]
                       + [rotate(spoke, 360 * i / cfg.SPOKES, origin=(0, 0)) for i in range(cfg.SPOKES)])
    return plan.difference(Point(0, 0).buffer(cfg.SCREW_HOLE_D / 2, quad_segs=quad))


def build_insert(cfg, *, screw_hub):
    """Single-dose insert: drops into the throat in place of the stock hopper.

    Args:
        cfg: Config namespace from load_config().
        screw_hub: Add a hub on the axis for the stock central hopper screw.

    Returns:
        trimesh.Trimesh in mm, spout down, z=0 on the bed.

    Raises:
        ValueError: The insert or hub parameters are inconsistent.
    """
    wall, _ = insert_profile(cfg)
    solid = revolve(wall, cfg.SEGMENTS)
    if screw_hub:
        solid += prism(_hub_plan(cfg), 0, cfg.HUB_H)
    return to_trimesh(solid)


def bellows_profile(cfg):
    """(r, z) profile of the bellows: cap, zig-zag folds, plug-in ring.

    The outer surface zig-zags between BELLOWS_OD/2 and BELLOWS_FOLD_DEPTH
    further in; the inner surface is that line moved in by BELLOWS_WALL. One
    last flank runs in to the ring, whose inside steps in to its own wall.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        (wall, void): shapely Polygons, the part's profile and its cavity.

    Raises:
        ValueError: The flanks are flatter than 45° from vertical, or the ring
            does not fit the socket or the folds.
    """
    r_out = cfg.BELLOWS_OD / 2
    r_in = r_out - cfg.BELLOWS_FOLD_DEPTH
    half = cfg.BELLOWS_FOLD_PITCH / 2
    r_ro = (cfg.SOCKET_ID - cfg.BELLOWS_FIT_CLEARANCE) / 2
    r_ri = r_ro - cfg.BELLOWS_RING_WALL
    flank = math.degrees(math.atan2(cfg.BELLOWS_FOLD_DEPTH, half))
    _check([
        (0 < flank <= MAX_OVERHANG, f"bellows flank {flank:.1f}° from vertical must be in (0, {MAX_OVERHANG:g}]: "
                                    "BELLOWS_FOLD_PITCH must be >= 2 * BELLOWS_FOLD_DEPTH"),
        (cfg.BELLOWS_RING_H <= cfg.SOCKET_DEPTH, "BELLOWS_RING_H must be <= SOCKET_DEPTH"),
        (0 < r_ri < r_ro < r_out, "ring must sit inside the fold peaks: SOCKET_ID - BELLOWS_FIT_CLEARANCE "
                                  "< BELLOWS_OD, and BELLOWS_RING_WALL < ring radius"),
    ])
    k = half / cfg.BELLOWS_FOLD_DEPTH  # rise per mm of radius along a flank
    z0 = cfg.BELLOWS_CAP_T
    folds = [(r_in if i % 2 else r_out, z0 + i * half) for i in range(2 * cfg.BELLOWS_FOLDS + 1)]
    z_peak = folds[-1][1]
    z_ring = z_peak + (r_out - r_ro) * k
    z_top = z_ring + cfg.BELLOWS_RING_H
    envelope = Polygon([(0, 0), (r_out, 0), *folds, (r_ro, z_ring), (r_ro, z_top), (0, z_top)])
    # inside: the outer line moved in, its last flank carried on until it passes the ring ID
    inner = LineString([*folds, (r_ri, z_peak + (r_out - r_ri) * k)]).offset_curve(cfg.BELLOWS_WALL).coords
    void = (Polygon([(0, inner[0][1]), *inner, (0, inner[-1][1])])
            .union(box(0, z_peak, r_ri, z_top + 1))
            .intersection(box(0, z0, r_out, z_top + 1)))
    return envelope.difference(void), void


def build_bellows(cfg):
    """TPU bellows: plugs into the insert socket; press it to blow out grounds.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        trimesh.Trimesh in mm, cap down, z=0 on the bed.

    Raises:
        ValueError: The bellows parameters are inconsistent.
    """
    wall, _ = bellows_profile(cfg)
    return to_trimesh(revolve(wall, cfg.SEGMENTS))
