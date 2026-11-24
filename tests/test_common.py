"""Tests for the manifold3d mesh helpers."""

import math

import pytest
from manifold3d import Manifold
from shapely.geometry import MultiPolygon, Polygon, box

from geometry.common import prism, revolve, to_trimesh


def test_prism_with_hole():
    """A square with a square hole extrudes to the right volume and z range."""
    ring = Polygon(box(0, 0, 10, 10).exterior.coords, [box(3, 3, 7, 7).exterior.coords])
    tm = to_trimesh(prism(ring, 2.0, 5.0))
    assert tm.is_watertight
    assert tm.volume == pytest.approx((100 - 16) * 3)
    assert tm.bounds.ravel().tolist() == pytest.approx([0, 0, 2, 10, 10, 5])


def test_prism_multipolygon():
    """Disjoint parts of a MultiPolygon each become a solid."""
    tm = to_trimesh(prism(MultiPolygon([box(0, 0, 1, 1), box(5, 0, 7, 1)]), 0, 2))
    assert tm.volume == pytest.approx(6.0)
    assert len(tm.split(only_watertight=True)) == 2


def test_revolve_axis_convention():
    """Profile x is the radius, profile y stays z: an annulus r 1..2, z 0..3."""
    segments = 128
    tm = to_trimesh(revolve(box(1, 0, 2, 3), segments))
    polygon_factor = segments / (2 * math.pi) * math.sin(2 * math.pi / segments)  # inscribed N-gon
    assert tm.is_watertight
    assert tm.volume == pytest.approx(math.pi * (4 - 1) * 3 * polygon_factor, rel=1e-6)
    assert tm.bounds[:, 2].tolist() == pytest.approx([0, 3])
    assert tm.bounds[:, :2].ravel().tolist() == pytest.approx([-2, -2, 2, 2], abs=1e-3)


def test_to_trimesh():
    """A manifold cube converts to a watertight 12-triangle box."""
    tm = to_trimesh(Manifold.cube((1, 2, 3)))
    assert tm.is_watertight
    assert tm.volume == pytest.approx(6.0)
    assert len(tm.faces) == 12
