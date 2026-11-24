"""Tests for generate.py's manifest logic (no meshes built)."""

import numpy as np
import pytest
import trimesh

from generate import GHOST_FILE, build_manifest, final_form, part_entry, row_major
from geometry.common import load_config
from geometry.grinder import grinder_on_base_pose, throat_pose
from geometry.hopper import kit_poses


def box_on_bed():
    """A 10 x 20 x 30 mm box standing on z=0.

    Returns:
        trimesh.Trimesh.
    """
    return trimesh.creation.box(extents=(10, 20, 30)).apply_translation((0, 0, 15))


def test_part_entry():
    """A watertight mesh on the bed becomes a complete manifest entry."""
    e = part_entry(box_on_bed(), "frederick-base-solid.stl", "Solid", "base")
    assert e["size_mm"] == [10.0, 20.0, 30.0]
    assert e["volume_cm3"] == 6.0
    assert e["triangles"] == 12
    assert e["material"] == "PLA/PETG" and "no supports" in e["hint"]


def test_part_entry_rejects_bad_meshes():
    """Open meshes and meshes off the bed are refused before export."""
    open_box = box_on_bed()
    open_box.update_faces([True] * 11 + [False])
    with pytest.raises(ValueError, match="watertight"):
        part_entry(open_box, "x.stl", "X", "insert")
    with pytest.raises(ValueError, match="z="):
        part_entry(box_on_bed().apply_translation((0, 0, 1)), "x.stl", "X", "insert")


def test_build_manifest_groups_and_parameters():
    """Entries keep their order inside their group; parameters follow the config."""
    cfg = load_config({"BASE_ANGLE": 12.0})
    e = part_entry(box_on_bed(), "a.stl", "A", "base")
    m = build_manifest(cfg, [("Angled base", e), ("Single-dose hopper", e), ("Angled base", e)])
    assert [g["name"] for g in m["groups"]] == ["Angled base", "Single-dose hopper"]
    assert len(m["groups"][0]["items"]) == 2
    params = dict(m["parameters"])
    assert params["Base angle"] == "12°"
    assert params["Spout OD"] == "33.6 mm"
    assert m["ghost"]["file"] == GHOST_FILE and GHOST_FILE.endswith(".stl")
    assert {"bases", "kits", "default"} <= set(m)


def test_row_major_round_trip():
    """Matrices go out row-major: reshape(4, 4) restores them; the translation sits at 3, 7, 11.

    three.js Matrix4.set() takes row-major arguments; fromArray() reads column-major,
    so it would see the transpose, which for a pose with a translation is a different matrix.
    """
    pose = trimesh.transformations.rotation_matrix(0.3, (1, 0, 0))
    pose[:3, 3] = (1, 2, 3)
    flat = row_major(pose)
    assert len(flat) == 16 and np.reshape(flat, (4, 4)) == pytest.approx(pose, abs=1e-6)
    assert [flat[3], flat[7], flat[11]] == [1, 2, 3] and flat[12:] == [0, 0, 0, 1]
    assert not np.allclose(np.reshape(flat, (4, 4), order="F"), pose)   # what fromArray() would build


def test_final_form_kits():
    """One manifest kit per HOPPER_KITS entry: its insert slot offers every variant, the other parts follow bottom
    up, and every part (each insert variant too) has a final placement, grinder_on_base_pose @ throat_pose @ kit pose.
    """
    cfg = load_config()
    ff = final_form(cfg)
    ghost = grinder_on_base_pose(cfg)
    inserts = {n: f"frederick-hopper-insert-{n}.stl" for n in cfg.INSERT_VARIANTS}
    assert [k["key"] for k in ff["kits"]] == list(cfg.HOPPER_KITS)
    for kit in ff["kits"]:
        parts = cfg.HOPPER_KITS[kit["key"]]
        assert kit["inserts"] == (inserts if "insert" in parts else {})
        assert kit["files"] == [f"frederick-hopper-{p}.stl" for p in parts if p != "insert"]
        assert set(kit["placements"]) == set(kit["inserts"].values()) | set(kit["files"])
        poses = kit_poses(cfg)[kit["key"]]
        for file, flat in kit["placements"].items():
            part = "insert" if file in inserts.values() else file.removeprefix("frederick-hopper-").removesuffix(".stl")
            m = np.reshape(flat, (4, 4))   # row-major: reshape gives the matrix back
            assert m == pytest.approx(ghost @ throat_pose(cfg) @ poses[part], abs=1e-5)
            assert m[3] == pytest.approx([0, 0, 0, 1]) and np.linalg.det(m[:3, :3]) == pytest.approx(1, abs=1e-5)
    assert ff["ghost"] == {"file": GHOST_FILE, "placement": row_major(ghost)}
    assert ff["bases"] == {n: f"frederick-base-{n}.stl" for n in cfg.BASE_VARIANTS}
    assert ff["default"] == {"base": "frame-solid", "kit": "3-part", "insert": "friction"}


def test_final_form_default_base_fallback():
    """Without a frame-solid variant the final form starts on the first base."""
    cfg = load_config({"BASE_VARIANTS": {"window": {"frame": False, "window": True}}})
    assert final_form(cfg)["default"]["base"] == "window"


@pytest.mark.parametrize("kind, material, hint", [("bellows-capped", "TPU 95A", "cap on the bed"),
                                                  ("bellows-open", "TPU 95A", "ring on the bed"),
                                                  ("2p-body", "TPU 95A", "spout down"),
                                                  ("cap", "PLA/PETG", "top face down")])
def test_hopper_print_info(kind, material, hint):
    """Each hopper part carries its own material and support-free print hint.

    Args:
        kind: PRINT_INFO key.
        material: Expected material.
        hint: Text the print hint must contain.
    """
    e = part_entry(box_on_bed(), "x.stl", "X", kind)
    assert e["material"] == material
    assert hint in e["hint"] and "no supports" in e["hint"]
