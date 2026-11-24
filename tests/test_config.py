"""Tests for config loading, validation and CLI overrides."""

import argparse

import pytest

from geometry.common import add_cli_args, config_from_args, load_config, validate


def parse(*argv):
    """Parse argv with the shared CLI options and load the config.

    Args:
        *argv: Command-line arguments.

    Returns:
        Config namespace.
    """
    return config_from_args(add_cli_args(argparse.ArgumentParser()).parse_args(list(argv)))


def test_defaults_load():
    """config.py loads and passes validation unchanged."""
    cfg = load_config()
    assert cfg.BASE_ANGLE == 10.0
    assert set(cfg.BASE_VARIANTS) == {"solid", "window", "frame-solid", "frame-window"}
    assert set(cfg.INSERT_VARIANTS) == {"friction", "screw"}
    assert list(cfg.HOPPER_KITS) == ["3-part", "capped-bellows", "two-piece"]


def test_override_applies_without_leaking():
    """An override changes only that load, not config.py's defaults."""
    cfg = load_config({"FOOT_D": 23.0})
    cfg.BASE_VARIANTS["solid"]["frame"] = True
    assert cfg.FOOT_D == 23.0
    fresh = load_config()
    assert fresh.FOOT_D == 22.4
    assert fresh.BASE_VARIANTS["solid"]["frame"] is False


def test_unknown_name_exits_with_suggestion():
    """A typo exits and names the close match."""
    with pytest.raises(SystemExit, match="BASE_ANGLE"):
        load_config({"BASE_ANGEL": 12})


@pytest.mark.parametrize("overrides", [
    {"BASE_ANGLE": 0},
    {"BASE_ANGLE": 31},
    {"FRAME_GAP": 5.0},               # frame wall 1 mm
    {"POCKET_DEPTH": 10.1},           # = FOOT_H
    {"SPOUT_WALL": 17.0},             # no spout bore left
    {"BELLOWS_FOLD_DEPTH": 35.0},     # folds meet in the middle
    {"HOPPER_KITS": {}},              # no kit for the preview to start on
])
def test_validate_rejects_bad_values(overrides):
    """Nonsense combinations raise ValueError.

    Args:
        overrides: Config overrides passed to load_config().
    """
    with pytest.raises(ValueError):
        load_config(overrides)


def test_validate_accepts_defaults():
    """validate() is silent on the defaults."""
    validate(load_config())


def test_set_and_angle_parsing():
    """--set takes Python literals (dicts too); --angle maps to BASE_ANGLE."""
    cfg = parse("--set", "FOOT_D=23", "--set", "BASE_VARIANTS={'solid': {'frame': False, 'window': False}}",
                "--angle", "12")
    assert cfg.FOOT_D == 23
    assert cfg.BASE_ANGLE == 12.0
    assert list(cfg.BASE_VARIANTS) == ["solid"]


def test_set_rejects_bad_input():
    """A missing '=' or a non-number for a numeric constant exits."""
    with pytest.raises(SystemExit, match="NAME=VALUE"):
        parse("--set", "FOOT_D")
    with pytest.raises(SystemExit, match="must be a number"):
        parse("--set", "FOOT_D=wide")   # not a literal -> kept as a string -> rejected
