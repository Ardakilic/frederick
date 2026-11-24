"""Tests for the grinder ghost (geometry/grinder.py), its poses and the preview's final form."""

import json
import os

import numpy as np
import pytest
import trimesh
from manifold3d import Manifold, Mesh64

from generate import ROOT, build_manifest, build_parts, final_form, part_entry
from geometry.common import load_config
from geometry.grinder import build_grinder_ghost, grinder_on_base_pose, throat_pose
from geometry.hopper import kit_poses

CFG = load_config()
FINAL = final_form(CFG)
OLD_FILES = ["frederick-hopper-bellows.stl", "frederick-hopper-2p-cap.stl"]   # renamed: -bellows-capped, -cap


def matrix(flat):
    """A manifest matrix back as 4x4.

    Args:
        flat: 16 floats, row-major (generate.row_major()).

    Returns:
        4x4 numpy array.
    """
    return np.reshape(flat, (4, 4))


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
    assert matrix(FINAL["ghost"]["placement"]) == pytest.approx(pose, abs=1e-6)   # what the final form draws
    assert (solid(base) ^ solid(ghost, pose)).volume() < 0.01
    feet = [(sx * CFG.FOOT_SPACING_X / 2, sy * CFG.FOOT_SPACING_Y / 2, -CFG.FOOT_H) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y, z in trimesh.transform_points(feet, pose):
        hit, _, _ = base.ray.intersects_location([[x, y, 500.0]], [[0, 0, -1.0]])
        assert hit[:, 2].max() == pytest.approx(z, abs=0.05)


@pytest.mark.parametrize("kit", CFG.HOPPER_KITS)
def test_throat_part_seats(kit, ghost, parts):
    """Each kit's first part, posed into the throat, does not cut into the ghost; 0.5 mm lower it does.

    Args:
        kit: HOPPER_KITS key.
        ghost: Ghost fixture.
        parts: Built parts fixture.
    """
    first = CFG.HOPPER_KITS[kit][0]
    pose = throat_pose(CFG) @ kit_poses(CFG)[kit][first]
    files = [f"frederick-hopper-insert-{n}.stl" for n in CFG.INSERT_VARIANTS] if first == "insert" \
        else [f"frederick-hopper-{first}.stl"]
    for file in files:
        mesh = parts[file][1]
        assert (solid(ghost) ^ solid(mesh, pose)).volume() < 0.01
        assert (solid(ghost) ^ solid(mesh, pose, 0.5)).volume() > 1


@pytest.mark.parametrize("kit", FINAL["kits"], ids=lambda k: k["key"])
def test_final_form_clear_of_ghost(kit, ghost, parts):
    """In the final form no kit part (every insert variant) cuts into the ghost.

    Exact poses, grinder_on_base_pose @ throat_pose @ kit pose: the manifest's
    copies are rounded to 6 decimals (about 1e-4 mm here), and test_generate
    checks they match these.

    Args:
        kit: One manifest kit (final_form()["kits"] entry).
        ghost: Ghost fixture.
        parts: Built parts fixture.
    """
    on_base = grinder_on_base_pose(CFG)
    poses = kit_poses(CFG)[kit["key"]]
    for file in kit["placements"]:
        part = "insert" if file in kit["inserts"].values() else file.removeprefix("frederick-hopper-").removesuffix(".stl")
        pose = on_base @ throat_pose(CFG) @ poses[part]
        assert matrix(kit["placements"][file]) == pytest.approx(pose, abs=1e-5)
        assert (solid(ghost, on_base) ^ solid(parts[file][1], pose)).volume() < 0.01, file


def test_final_form_files_exist(parts):
    """Every base and kit file the final form names is a built part; bases map to base STLs.

    Args:
        parts: Built parts fixture.
    """
    assert set(FINAL["bases"].values()) == {f for f, (kind, _) in parts.items() if kind == "base"}
    for kit in FINAL["kits"]:
        assert set(kit["placements"]) <= set(parts)
    assert FINAL["default"]["base"] in FINAL["bases"]


def test_rename_took(parts):
    """The old bellows and cap file names are gone from the manifest and from stl/; stl/ holds exactly the parts.

    Args:
        parts: Built parts fixture.
    """
    manifest = build_manifest(CFG, [("g", part_entry(mesh, file, "x", kind)) for file, (kind, mesh) in parts.items()])
    text = json.dumps(manifest)
    on_disk = set(os.listdir(os.path.join(ROOT, "stl")))
    for old in OLD_FILES:
        assert old not in text and old not in on_disk
    assert on_disk == set(parts)
