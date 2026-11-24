"""Angled base stand: a wedge that tilts the grinder forward, its feet in blind pockets.

World: X left-right centred on 0, Y front -> back with the footprint's front
edge at Y=0, Z up, bed at z=0. The deck is the tilted top plane, rising toward
+Y at BASE_ANGLE (a). Deck frame: origin (0, 0, BASE_FRONT_H), x = world X,
u = (0, cos a, sin a) up the slope, w = (0, -sin a, cos a) the deck normal.
Pockets and the frame recess are built in the deck frame (walls perpendicular
to the deck); the outer walls, window and pad recesses are world-vertical.
"""

import math

import numpy as np
from manifold3d import Manifold
from shapely.geometry import MultiPolygon, Point, Polygon, box

from geometry.common import prism, revolve, to_trimesh

EPS = 0.01  # mm, cutters overshoot the bed by this so they never share a face with it


def _rounded_rect(x0, y0, x1, y1, r, segments):
    """Axis-aligned rectangle with its corners rounded.

    Args:
        x0: Left edge.
        y0: Bottom edge.
        x1: Right edge.
        y1: Top edge.
        r: Corner radius, 0 <= r < half the shorter side.
        segments: Segments per full circle.

    Returns:
        shapely Polygon.
    """
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=max(1, segments // 4))


def deck_to_world(cfg):
    """The deck frame as a transform: deck coordinates (x, u, w) -> world coordinates.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        4x4 numpy array: x = world X, u up the slope, w the deck normal,
        origin at (0, 0, BASE_FRONT_H).
    """
    a = math.radians(cfg.BASE_ANGLE)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, cfg.BASE_FRONT_H], [0, 0, 0, 1]])


def _to_world(cfg, m):
    """Map a Manifold built in deck coordinates (x, u, w) into world coordinates.

    Args:
        cfg: Config namespace from load_config().
        m: manifold3d.Manifold in the deck frame.

    Returns:
        manifold3d.Manifold in the world frame.
    """
    return m.transform(deck_to_world(cfg)[:3])


def build_base(cfg, *, frame, window):
    """Build one angled base variant.

    Args:
        cfg: Config namespace from load_config().
        frame: Add a rim around the grinder plate (with the cable notch).
        window: Cut a vertical through-window between the pocket rows.

    Returns:
        trimesh.Trimesh in mm, in print orientation (bottom on z=0, deck up).

    Raises:
        ValueError: The parameters give a broken part (pocket outside the
            deck or biting the frame wall, floor too thin, window too small,
            pad recess hitting the window, recess through the front wall).
    """
    a = math.radians(cfg.BASE_ANGLE)
    sin_a, cos_a = math.sin(a), math.cos(a)
    seg = cfg.SEGMENTS
    pd, cham = cfg.POCKET_DEPTH, cfg.POCKET_CHAMFER
    wd = cfg.GRINDER_PLATE_W + 2 * cfg.BASE_EDGE_MARGIN   # deck width
    ld = cfg.GRINDER_PLATE_D + 2 * cfg.BASE_EDGE_MARGIN   # deck length along the slope
    lf = ld * cos_a                                       # footprint depth
    big = 2 * (wd + ld)                                   # longer than any part dimension
    rise = cfg.FOOT_H - pd + cfg.FRAME_OVERLAP if frame else 0.0   # rim top above the deck
    wall = cfg.BASE_EDGE_MARGIN - cfg.FRAME_GAP           # frame wall thickness at the deck
    r = (cfg.FOOT_D + cfg.FOOT_CLEARANCE) / 2             # pocket radius
    mouth = r + cham                                      # pocket radius at the chamfered mouth
    u_front = (ld - cfg.FOOT_SPACING_Y) / 2               # front pocket row; the back row mirrors it
    u_back = ld - u_front
    inset = wall if frame else 0.0                        # pocket mouths stay this far inside the deck

    errors = []
    if not 0 <= cham < pd:
        errors.append("POCKET_CHAMFER must be >= 0 and < POCKET_DEPTH")
    if cfg.FOOT_SPACING_X / 2 + mouth > wd / 2 - inset or u_front - mouth < inset:
        where = "into the frame wall" if frame else "past the deck edge"
        errors.append(f"foot pockets (mouth Ø{2 * mouth:g}) reach {where}; check FOOT_SPACING_X/Y, "
                      "BASE_EDGE_MARGIN, FRAME_GAP")
    floor = cfg.BASE_FRONT_H + (u_front - r) * sin_a - pd * cos_a - cfg.PAD_DEPTH
    if floor < cfg.BASE_MIN_WALL:
        errors.append(f"front pocket floor is {floor:.2f} mm above the bottom (pad recess counted), "
                      "< BASE_MIN_WALL; raise BASE_FRONT_H or lower POCKET_DEPTH / PAD_DEPTH")
    thinnest = wall - rise * math.tan(a)   # front frame wall at the rim top (recess wall leans forward)
    if frame and thinnest < cfg.BASE_MIN_WALL:
        errors.append(f"thinnest frame wall (front, at the rim top) is {thinnest:.2f} mm < BASE_MIN_WALL; "
                      "raise BASE_EDGE_MARGIN or lower FRAME_OVERLAP")

    pads = MultiPolygon([Point(sx * (wd / 2 - cfg.PAD_INSET), y).buffer(cfg.PAD_D / 2, quad_segs=seg // 4)
                         for sx in (-1, 1) for y in (cfg.PAD_INSET, lf - cfg.PAD_INSET)])
    if window:
        # The pocket is perpendicular to the deck, the window wall vertical: keep the
        # rail at both the pocket mouth (w=0) and its floor (w=-pd).
        hw = wd / 2 - cfg.WINDOW_SIDE_RAIL
        y0 = max((u_front + mouth) * cos_a, (u_front + r) * cos_a + pd * sin_a) + cfg.WINDOW_END_RAIL
        y1 = min((u_back - mouth) * cos_a, (u_back - r) * cos_a + pd * sin_a) - cfg.WINDOW_END_RAIL
        if min(hw, (y1 - y0) / 2) <= cfg.WINDOW_CORNER_R:
            errors.append(f"window would be {2 * hw:.1f} x {y1 - y0:.1f} mm, too small for WINDOW_CORNER_R; "
                          "lower WINDOW_SIDE_RAIL / WINDOW_END_RAIL")
        else:
            hole = _rounded_rect(-hw, y0, hw, y1, cfg.WINDOW_CORNER_R, seg)
            if cfg.PAD_DEPTH > 0 and pads.distance(hole) < cfg.BASE_MIN_WALL:
                errors.append("pad recesses come within BASE_MIN_WALL of the window; change PAD_INSET")
    if errors:
        raise ValueError("base error:\n  " + "\n  ".join(errors))

    below = Manifold.cube((2 * big, 2 * big, big + rise)).translate((-big, -big, -big))
    body = prism(_rounded_rect(-wd / 2, 0, wd / 2, lf, cfg.BASE_CORNER_R, seg), 0, big) ^ _to_world(cfg, below)

    pocket = revolve(Polygon([(0, -pd), (r, -pd), (r, -cham), (mouth, 0), (mouth, pd), (0, pd)]), seg)
    cut = Manifold()
    for sx in (-1, 1):
        for u in (u_front, u_back):
            cut += pocket.translate((sx * cfg.FOOT_SPACING_X / 2, u, 0))
    if frame:
        top = rise + pd
        cut += prism(_rounded_rect(-wd / 2 + wall, wall, wd / 2 - wall, ld - wall, cfg.FRAME_GAP, seg), 0, top)
        if cfg.CABLE_NOTCH_W > 0:
            x, half = cfg.CABLE_NOTCH_X, cfg.CABLE_NOTCH_W / 2
            cut += prism(box(x - half, ld / 2, x + half, ld + big), 0, top)
    body -= _to_world(cfg, cut)

    if window:
        body -= prism(hole, -EPS, big)
    if cfg.PAD_DEPTH > 0:
        body -= prism(pads, -EPS, cfg.PAD_DEPTH)
    return to_trimesh(body)
