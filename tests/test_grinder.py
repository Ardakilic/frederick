"""Tests for the grinder ghost (geometry/grinder.py), its poses and the preview placements."""

import numpy as np
import pytest
import trimesh
from manifold3d import Manifold, Mesh64

from generate import build_parts, view_fields
from geometry.common import load_config
from geometry.grinder import build_grinder_ghost, grinder_on_base_pose, grinder_upright_pose, throat_pose
from geometry.hopper import assembly_poses

CFG = load_config()
SEATED = ["frederick-hopper-insert-friction.stl", "frederick-hopper-insert-screw.stl", "frederick-hopper-2p-body.stl"]


@pytest.fixture(scope="module")
def ghost():
    """The default grinder ghost.

    Returns:
        trimesh.Trimesh in the grinder frame.
    """
    return build_grinder_ghost(CFG)


@pytest.fixture(scope="module")
def parts():
    """Every part generate.py builds.

    Returns:
        Dict STL file name -> (kind, trimesh.Trimesh).
    """
    return {file: (kind, mesh) for _, file, _, kind, mesh in build_parts(CFG)}


def solid(mesh, pose=np.eye(4), dz=0.0):
    """A mesh moved by a pose, then lowered by dz, as a manifold3d solid for booleans.

    Args:
        mesh: trimesh.Trimesh.
        pose: 4x4 transform.
        dz: Extra drop along world z (mm).

    Returns:
        manifold3d.Manifold.
    """
    vertices = trimesh.transform_points(mesh.vertices, pose) - (0, 0, dz)
    return Manifold(Mesh64(vert_properties=np.ascontiguousarray(vertices, dtype=np.float64),
                           tri_verts=np.ascontiguousarray(mesh.faces, dtype=np.uint64)))


def test_ghost_is_one_watertight_body(ghost):
    """One closed body from the foot bottoms (-FOOT_H) up to about the ring top (the knob is centred there).

    Args:
        ghost: Ghost fixture.
    """
    assert ghost.is_watertight and ghost.body_count == 1
    assert ghost.bounds[0][2] == pytest.approx(-CFG.FOOT_H)
    assert CFG.GHOST_RING_TOP <= ghost.bounds[1][2] <= CFG.GHOST_RING_TOP + CFG.GHOST_KNOB_D / 2 + 1e-6


def test_ghost_frame_and_throat(ghost):
    """The knob is on the right (+X, as CABLE_NOTCH_X), behind the ring; the throat bore is open to its floor.

    Args:
        ghost: Ghost fixture.
    """
    ring_y = CFG.GRINDER_PLATE_D / 2 - CFG.GHOST_RING_FROM_BACK
    knob = ghost.section(plane_origin=(0, 0, CFG.GHOST_RING_TOP + 1), plane_normal=(0, 0, 1)).vertices
    assert knob[:, 0].min() == pytest.approx(0, abs=1e-6) and knob[:, 0].max() == pytest.approx(CFG.GHOST_KNOB_L)
    assert (knob[:, 1].min() + knob[:, 1].max()) / 2 == pytest.approx(ring_y + CFG.GHOST_KNOB_BEHIND, abs=1e-3)
    hit, _, _ = ghost.ray.intersects_location([[0, ring_y, 500.0]], [[0, 0, -1.0]])
    assert hit[:, 2].max() == pytest.approx(CFG.GHOST_RING_TOP - CFG.THROAT_DEPTH)
    assert throat_pose(CFG)[:3, 3] == pytest.approx([0, ring_y, CFG.GHOST_RING_TOP - CFG.THROAT_DEPTH])


def test_ghost_rejects_bad_config():
    """A ring below the shell top, or narrower than the throat, is refused."""
    with pytest.raises(ValueError, match="grinder ghost"):
        build_grinder_ghost(load_config({"GHOST_SHELL_TOP": 195.0}))
    with pytest.raises(ValueError, match="grinder ghost"):
        build_grinder_ghost(load_config({"GHOST_RING_D": 30.0}))


@pytest.mark.parametrize("name", CFG.BASE_VARIANTS)
def test_ghost_sits_on_base(name, ghost, parts):
    """On every base the ghost does not cut into it, and each foot bottom is on its pocket floor (0.05 mm).

    Args:
        name: Variant key from BASE_VARIANTS.
        ghost: Ghost fixture.
        parts: Built parts fixture.
    """
    base = parts[f"frederick-base-{name}.stl"][1]
    pose = grinder_on_base_pose(CFG)
    assert (solid(base) ^ solid(ghost, pose)).volume() < 0.01
    feet = [(sx * CFG.FOOT_SPACING_X / 2, sy * CFG.FOOT_SPACING_Y / 2, -CFG.FOOT_H) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y, z in trimesh.transform_points(feet, pose):
        hit, _, _ = base.ray.intersects_location([[x, y, 500.0]], [[0, 0, -1.0]])
        assert hit[:, 2].max() == pytest.approx(z, abs=0.05)


def test_ghost_upright(ghost):
    """Standing upright, the feet bottoms are on the table (z = 0).

    Args:
        ghost: Ghost fixture.
    """
    assert trimesh.transform_points(ghost.vertices, grinder_upright_pose(CFG))[:, 2].min() == pytest.approx(0)


@pytest.mark.parametrize("file", SEATED)
def test_hopper_seats_in_throat(file, ghost, parts):
    """Posed into the throat, the spout part does not cut into the ghost; 0.5 mm lower it does.

    Args:
        file: STL file name of a part with the spout.
        ghost: Ghost fixture.
        parts: Built parts fixture.
    """
    mesh = parts[file][1]
    pose = throat_pose(CFG) @ assembly_poses(CFG)[file.removesuffix(".stl")]
    assert (solid(ghost) ^ solid(mesh, pose)).volume() < 0.01
    assert (solid(ghost) ^ solid(mesh, pose, 0.5)).volume() > 1


def test_every_part_has_a_placement(parts):
    """Every STL gets valid row-major placements: rigid motions, last row 0 0 0 1, partners that exist.

    Args:
        parts: Built parts fixture.
    """
    up = grinder_upright_pose(CFG)
    for file, (kind, _) in parts.items():
        fields = view_fields(CFG, file, kind)
        for key in ("placement", "ghost_placement"):
            m = np.reshape(fields[key], (4, 4))   # row-major: reshape gives the matrix back
            assert np.isfinite(m).all() and m[3] == pytest.approx([0, 0, 0, 1])
            assert m[:3, :3] @ m[:3, :3].T == pytest.approx(np.eye(3), abs=1e-5)
            assert np.linalg.det(m[:3, :3]) == pytest.approx(1, abs=1e-5)
        assert set(fields["partners"]) <= set(parts) and file not in fields["partners"]
        if kind == "base":
            assert fields["placement"] == pytest.approx(np.eye(4).ravel())
            assert fields["ghost_placement"] == pytest.approx(grinder_on_base_pose(CFG).ravel(), abs=1e-6)
        else:
            expected = up @ throat_pose(CFG) @ assembly_poses(CFG)[file.removesuffix(".stl")]
            assert fields["placement"] == pytest.approx(expected.ravel(), abs=1e-6)
            assert fields["ghost_placement"] == pytest.approx(up.ravel())
            assert fields["partners"]
