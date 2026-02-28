"""Testy pro rozšířený project_io (snapshoty, crash report, bundle)."""

import json
import tempfile
from pathlib import Path

import pytest

from archpapercraft.project_io.project import Project, ProjectSettings
from archpapercraft.scene_graph.node import NodeType


class TestSnapshots:
    def test_create_snapshot(self):
        proj = Project(settings=ProjectSettings(name="SnapTest"))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.apcraft"
            proj.save(path)
            snap = proj.create_snapshot("v1")
            assert snap is not None
            assert snap.exists()
            assert "v1" in snap.name

    def test_list_snapshots(self):
        proj = Project(settings=ProjectSettings(name="ListTest"))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.apcraft"
            proj.save(path)
            proj.create_snapshot("a")
            proj.create_snapshot("b")
            snaps = proj.list_snapshots()
            assert len(snaps) == 2

    def test_load_snapshot(self):
        proj = Project(settings=ProjectSettings(name="LoadTest"))
        proj.scene.add_node("Box", NodeType.PRIMITIVE_BOX)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.apcraft"
            proj.save(path)
            snap = proj.create_snapshot()
            assert snap is not None
            loaded = Project.load_snapshot(snap)
            assert loaded.settings.name == "LoadTest"

    def test_no_snapshot_without_save(self):
        proj = Project()
        result = proj.create_snapshot()
        assert result is None


class TestCrashReport:
    def test_write_crash_report(self):
        try:
            raise ValueError("Testovací chyba")
        except ValueError as exc:
            path = Project.write_crash_report(exc)
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "Testovací chyba" in content
            # Úklid
            path.unlink(missing_ok=True)

    def test_list_crash_reports(self):
        reports = Project.list_crash_reports()
        assert isinstance(reports, list)


class TestBundleExport:
    def test_export_bundle(self):
        proj = Project(settings=ProjectSettings(name="BundleTest"))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "test.apcraft"
            proj.save(path)
            proj.create_snapshot("v1")
            bundle = proj.export_bundle()
            assert bundle.exists()
            assert bundle.suffix == ".zip"

    def test_bundle_without_save_raises(self):
        proj = Project()
        with pytest.raises(ValueError):
            proj.export_bundle()
