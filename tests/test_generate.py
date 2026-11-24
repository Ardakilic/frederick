"""Tests for generate.py's manifest logic (no geometry modules needed)."""

import pytest
import trimesh

from generate import build_manifest, part_entry
from geometry.common import load_config


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
