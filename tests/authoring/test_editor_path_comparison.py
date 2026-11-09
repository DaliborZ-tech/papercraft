"""Harmless closing-line serialization must not hide changed native geometry."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "author_editor_probe", Path(__file__).resolve().parents[2] / "tools/authoring/editor_probe.py",
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_explicit_straight_close_and_implicit_z_preserve_native_cubic_geometry():
    probe._same_path(
        "M 0 0 C 20 30 60 30 80 0 L 80 -10 L 0 -10 L 0 0 Z",
        "m 0,0 c 20,30 60,30 80,0 v -10 h -80 z",
    )


def test_every_subpath_keeps_its_own_exact_closing_point():
    probe._same_path("M .1 .2 L .3 .4 L .1 .2 Z M 10 20 L 20 20 L 20 30 L 10 20 Z",
                     "m .1 .2 l .2 .2 z m 9.9 19.8 h 10 v 10 z")


@pytest.mark.parametrize("before,after", [
    ("M 0 0 C 1 2 3 4 0 0 Z", "M 0 0 L 0 0 Z"),
    ("M 0 0 A 5 5 0 0 1 10 0 L 0 0 Z", "M 0 0 L 10 0 Z"),
    ("M 0 0 L 10 0 L 10 10 L .000001 0 Z", "M 0 0 L 10 0 L 10 10 Z"),
    ("M 0 0 L 10 0 L 10 10 Z", "M 0 0 L 10 0 L 11 10 Z"),
])
def test_canonical_closure_never_removes_curves_or_a_different_short_closing_edge(before, after):
    with pytest.raises(AssertionError):
        probe._same_path(before, after)
