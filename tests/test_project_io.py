"""Tests for project_io: save, load, autosave, recovery."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from archpapercraft.project_io.project import Project, ProjectSettings
from archpapercraft.scene_graph.node import NodeType


class TestProjectSettings:
    def test_scale_factor(self):
        s = ProjectSettings(scale="1:100")
        assert s.scale_factor == pytest.approx(0.01)

    def test_roundtrip(self):
        s = ProjectSettings(name="Test", units="cm", scale="1:50", paper="A3")
        d = s.to_dict()
        s2 = ProjectSettings.from_dict(d)
        assert s2.name == "Test"
        assert s2.units == "cm"
        assert s2.scale == "1:50"


class TestProjectSaveLoad:
    def test_save_and_load(self):
        proj = Project(settings=ProjectSettings(name="Demo"))
        proj.scene.add_node("TestBox", NodeType.PRIMITIVE_BOX, dx=2.0, dy=3.0, dz=4.0)

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.apcraft"
            proj.save(path)
            assert path.exists()

            loaded = Project.load(path)
            assert loaded.settings.name == "Demo"
            nodes = loaded.scene.root.children
            assert len(nodes) == 1
            assert nodes[0].name == "TestBox"
            assert nodes[0].parameters["dx"] == 2.0

    def test_autosave(self):
        proj = Project(settings=ProjectSettings(name="AutoTest"))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "auto.apcraft"
            proj.save(path)
            auto = proj.autosave()
            assert auto is not None
            assert auto.exists()

    def test_recovery(self):
        proj = Project(settings=ProjectSettings(name="Recover"))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "recover.apcraft"
            proj.save(path)
            proj.autosave()

            recovered = Project.recover(path)
            assert recovered is not None
            assert recovered.settings.name == "Recover"
