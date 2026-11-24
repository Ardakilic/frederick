"""Grinder ghost: a boxy, approximate, self-made stand-in for the Lelit Fred, for the preview only.

No usable model of the Fred exists, so this is built from the GHOST_* estimates
in config.py: context, not a measured model. It is never exported to stl/.
Grinder frame: origin at the centre of the base plate's underside, z up,
Y front -> back, +X = right when facing the grinder's front (as in base.py).
"""

from manifold3d import Manifold
from trimesh.transformations import translation_matrix

from geometry.base import deck_to_world
from geometry.common import to_trimesh


def _box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box between two corners.

    Args:
        x0: Left.
        x1: Right.
        y0: Front.
        y1: Back.
        z0: Bottom.
        z1: Top.

    Returns:
        manifold3d.Manifold.
    """
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def _cylinder(cfg, d, x, y, z0, z1):
    """Vertical cylinder.

    Args:
        cfg: Config namespace (for SEGMENTS).
        d: Diameter.
        x: Axis X.
        y: Axis Y.
        z0: Bottom.
        z1: Top.

    Returns:
        manifold3d.Manifold.
    """
    return Manifold.cylinder(z1 - z0, d / 2, circular_segments=cfg.SEGMENTS).translate((x, y, z0))


def build_grinder_ghost(cfg):
    """The grinder as one simple solid: plate, feet, shell, chute tower, housing, ring, fork, knob.

    Attached pieces run into their neighbour, so the union is one body.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        trimesh.Trimesh in the grinder frame (feet down to z = -FOOT_H).

    Raises:
        ValueError: The ring is not above the shell or not wider than the throat.
    """
    ring_bottom = cfg.GHOST_RING_TOP - cfg.GHOST_RING_H
    if not (cfg.GHOST_SHELL_TOP < ring_bottom and cfg.THROAT_ID < cfg.GHOST_RING_D):
        raise ValueError("grinder ghost: need GHOST_SHELL_TOP < GHOST_RING_TOP - GHOST_RING_H "
                         "and THROAT_ID < GHOST_RING_D")
    back = cfg.GRINDER_PLATE_D / 2
    front = back - cfg.GHOST_SHELL_D            # shell front face
    ring_y = back - cfg.GHOST_RING_FROM_BACK
    w, sw, cw, t = cfg.GRINDER_PLATE_W / 2, cfg.GHOST_SHELL_W / 2, cfg.GHOST_CHUTE_W / 2, cfg.GHOST_FORK_T / 2
    ghost = _box(-w, w, -back, back, 0, cfg.GHOST_PLATE_T)
    ghost += _box(-sw, sw, front, back, 0, cfg.GHOST_SHELL_TOP)
    ghost += _box(-cw, cw, front - cfg.GHOST_CHUTE_PROUD, back, cfg.GHOST_CHUTE_BOTTOM, cfg.GHOST_SHELL_TOP)
    ghost += _cylinder(cfg, cfg.GHOST_HOUSING_D, 0, ring_y, 0, ring_bottom)
    ghost += _cylinder(cfg, cfg.GHOST_RING_D, 0, ring_y, ring_bottom, cfg.GHOST_RING_TOP)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ghost += _cylinder(cfg, cfg.FOOT_D, sx * cfg.FOOT_SPACING_X / 2, sy * cfg.FOOT_SPACING_Y / 2,
                               -cfg.FOOT_H, cfg.GHOST_PLATE_T / 2)
        x = sx * cfg.GHOST_FORK_GAP / 2
        ghost += _box(x - t, x + t, front - cfg.GHOST_FORK_REACH, back, cfg.GHOST_FORK_Z - t, cfg.GHOST_FORK_Z + t)
    knob = Manifold.cylinder(cfg.GHOST_KNOB_L, cfg.GHOST_KNOB_D / 2, circular_segments=cfg.SEGMENTS)
    ghost += knob.rotate((0, 90, 0)).translate((0, ring_y + cfg.GHOST_KNOB_BEHIND, cfg.GHOST_RING_TOP))
    ghost -= _cylinder(cfg, cfg.THROAT_ID, 0, ring_y, cfg.GHOST_RING_TOP - cfg.THROAT_DEPTH, cfg.GHOST_RING_TOP + 1)
    return to_trimesh(ghost)


def throat_pose(cfg):
    """Hopper frame -> grinder frame: the spout bottom on the throat floor, the collar on the ring top.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        4x4 numpy array; the hopper frame is the one hopper.kit_poses() maps into.
    """
    ring_y = cfg.GRINDER_PLATE_D / 2 - cfg.GHOST_RING_FROM_BACK
    return translation_matrix((0, ring_y, cfg.GHOST_RING_TOP - cfg.THROAT_DEPTH))


def grinder_on_base_pose(cfg):
    """Grinder frame -> base world frame: plate centred on the deck, feet on the pocket floors.

    Args:
        cfg: Config namespace from load_config().

    Returns:
        4x4 numpy array, tilted with the deck (reuses base.deck_to_world).
    """
    deck_centre = cfg.GRINDER_PLATE_D / 2 + cfg.BASE_EDGE_MARGIN
    return deck_to_world(cfg) @ translation_matrix((0, deck_centre, cfg.FOOT_H - cfg.POCKET_DEPTH))
