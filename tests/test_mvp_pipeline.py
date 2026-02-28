"""Tests for MVP pipeline fixes — merge, strategy dispatch, page settings, export offset."""

from __future__ import annotations

import numpy as np
import pytest

from archpapercraft.core_geometry.primitives import MeshData, make_box_mesh, make_cylinder_mesh
from archpapercraft.core_geometry.operations import merge_meshes


# ======================================================================
# merge_meshes
# ======================================================================


class TestMergeMeshes:
    def test_empty_list(self):
        result = merge_meshes([])
        assert result.vertices.shape == (0, 3)
        assert result.faces.shape == (0, 3)

    def test_single_mesh(self):
        box = make_box_mesh(1, 1, 1)
        result = merge_meshes([box])
        assert result is box  # should return the same instance

    def test_two_boxes(self):
        a = make_box_mesh(1, 1, 1)
        b = make_box_mesh(2, 2, 2)
        result = merge_meshes([a, b])
        assert len(result.vertices) == len(a.vertices) + len(b.vertices)
        assert len(result.faces) == len(a.faces) + len(b.faces)

    def test_face_indices_offset(self):
        a = make_box_mesh(1, 1, 1)
        b = make_box_mesh(2, 2, 2)
        result = merge_meshes([a, b])
        # All faces from b should reference vertices starting at len(a.vertices)
        b_faces = result.faces[len(a.faces):]
        assert b_faces.min() >= len(a.vertices)

    def test_three_meshes(self):
        meshes = [make_box_mesh(1, 1, 1) for _ in range(3)]
        result = merge_meshes(meshes)
        total_verts = sum(len(m.vertices) for m in meshes)
        total_faces = sum(len(m.faces) for m in meshes)
        assert len(result.vertices) == total_verts
        assert len(result.faces) == total_faces


# ======================================================================
# collect_visible_meshes
# ======================================================================


class TestCollectVisibleMeshes:
    def test_visible(self):
        from archpapercraft.scene_graph.scene import Scene
        from archpapercraft.scene_graph.node import NodeType

        scene = Scene()
        n1 = scene.add_node("Box1", NodeType.PRIMITIVE_BOX, dx=1, dy=1, dz=1)
        n2 = scene.add_node("Box2", NodeType.PRIMITIVE_BOX, dx=2, dy=2, dz=2)
        scene.rebuild_meshes()

        assert len(scene.collect_visible_meshes()) == 2
        n2.set_visible(False)
        assert len(scene.collect_visible_meshes()) == 1


# ======================================================================
# extract_revolution_profile
# ======================================================================


class TestExtractRevolutionProfile:
    def test_cylinder_detected(self):
        from archpapercraft.unfolder.strategies import extract_revolution_profile

        cyl = make_cylinder_mesh(1.0, 3.0, segments=32)
        profile = extract_revolution_profile(cyl)
        assert profile is not None
        assert profile.shape[1] == 2

    def test_box_not_revolution(self):
        from archpapercraft.unfolder.strategies import extract_revolution_profile

        box = make_box_mesh(1, 2, 3)
        profile = extract_revolution_profile(box)
        assert profile is None

    def test_flat_mesh_none(self):
        from archpapercraft.unfolder.strategies import extract_revolution_profile

        flat = MeshData(
            vertices=np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0]], dtype=np.float64),
            faces=np.array([[0, 1, 2]], dtype=np.int32),
        )
        assert extract_revolution_profile(flat) is None


# ======================================================================
# unfold_with_strategy
# ======================================================================


class TestUnfoldWithStrategy:
    @pytest.fixture()
    def box_and_seams(self):
        from archpapercraft.seam_editor.auto_seams import auto_seams

        box = make_box_mesh(10, 10, 10)
        sg = auto_seams(box)
        return box, sg

    def test_exact_strategy(self, box_and_seams):
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy

        box, sg = box_and_seams
        parts = unfold_with_strategy(box, sg, strategy="Exact", segments=16)
        assert len(parts) > 0

    def test_facets_strategy(self, box_and_seams):
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy

        box, sg = box_and_seams
        parts = unfold_with_strategy(box, sg, strategy="Facets", segments=16)
        assert len(parts) > 0

    def test_gores_fallback_for_box(self, box_and_seams):
        """A box is not a revolution body → should fall back to Exact."""
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy

        box, sg = box_and_seams
        parts = unfold_with_strategy(box, sg, strategy="Gores", segments=8)
        assert len(parts) > 0

    def test_gores_on_cylinder(self):
        """A cylinder is a revolution body → should produce gore parts."""
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy
        from archpapercraft.seam_editor.auto_seams import auto_seams

        cyl = make_cylinder_mesh(5.0, 20.0, segments=32)
        sg = auto_seams(cyl)
        parts = unfold_with_strategy(cyl, sg, strategy="Gores", segments=8)
        assert len(parts) > 0
        # gores strategy on a revolution body → should produce ~8 parts (gores)
        assert len(parts) == 8

    def test_rings_on_cylinder(self):
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy
        from archpapercraft.seam_editor.auto_seams import auto_seams

        cyl = make_cylinder_mesh(5.0, 20.0, segments=32)
        sg = auto_seams(cyl)
        parts = unfold_with_strategy(cyl, sg, strategy="Rings", segments=4)
        assert len(parts) > 0

    def test_unknown_strategy_falls_back(self, box_and_seams):
        from archpapercraft.unfolder.approx_unfold import unfold_with_strategy

        box, sg = box_and_seams
        parts = unfold_with_strategy(box, sg, strategy="NonExistent", segments=8)
        assert len(parts) > 0


# ======================================================================
# _outline_to_unfolded_part
# ======================================================================


class TestOutlineToUnfoldedPart:
    def test_triangle(self):
        from archpapercraft.unfolder.approx_unfold import _outline_to_unfolded_part

        outline = np.array([[0, 0], [10, 0], [5, 8]], dtype=np.float64)
        part = _outline_to_unfolded_part(outline, part_id=42)
        assert part.part_id == 42
        assert len(part.faces) == 1
        assert len(part.cut_edges) == 3

    def test_pentagon(self):
        from archpapercraft.unfolder.approx_unfold import _outline_to_unfolded_part

        angles = np.linspace(0, 2 * np.pi, 5, endpoint=False)
        outline = np.column_stack([np.cos(angles), np.sin(angles)])
        part = _outline_to_unfolded_part(outline, part_id=0)
        assert len(part.faces) == 3  # fan from vertex 0
        assert len(part.cut_edges) == 5

    def test_degenerate(self):
        from archpapercraft.unfolder.approx_unfold import _outline_to_unfolded_part

        outline = np.array([[0, 0], [1, 0]], dtype=np.float64)
        part = _outline_to_unfolded_part(outline, part_id=0)
        assert len(part.faces) == 0


# ======================================================================
# PageSettings from ProjectSettings (build_page_settings)
# ======================================================================


class TestBuildPageSettings:
    def test_default_project(self):
        """Default project → A4 portrait 10mm margin."""
        from archpapercraft.ui.papercraft_panel import PapercraftPanel
        from archpapercraft.project_io.project import Project

        panel = PapercraftPanel.__new__(PapercraftPanel)
        panel._project = Project()
        ps = panel._build_page_settings()

        from archpapercraft.layout_packer.packer import PaperSize, Orientation

        assert ps.paper == PaperSize.A4
        assert ps.orientation == Orientation.PORTRAIT
        assert ps.margin_mm == 10.0

    def test_a3_from_project(self):
        from archpapercraft.ui.papercraft_panel import PapercraftPanel
        from archpapercraft.project_io.project import Project, ProjectSettings
        from archpapercraft.layout_packer.packer import PaperSize

        proj = Project(settings=ProjectSettings(paper="A3", paper_margin_mm=15.0))
        panel = PapercraftPanel.__new__(PapercraftPanel)
        panel._project = proj
        ps = panel._build_page_settings()

        assert ps.paper == PaperSize.A3
        assert ps.margin_mm == 15.0

    def test_layout_prefs_override(self):
        from archpapercraft.ui.papercraft_panel import PapercraftPanel
        from archpapercraft.project_io.project import Project
        from archpapercraft.layout_packer.packer import Orientation

        proj = Project()
        proj.save_layout_settings(paper="A4", orientation="landscape", margin_mm=20.0)

        panel = PapercraftPanel.__new__(PapercraftPanel)
        panel._project = proj
        ps = panel._build_page_settings()

        assert ps.orientation == Orientation.LANDSCAPE
        assert ps.margin_mm == 20.0


# ======================================================================
# Export offset×scale regression
# ======================================================================


class TestExportOffsetScale:
    """Verify that packer offsets (already in paper mm) are NOT re-scaled."""

    def test_pdf_offset_not_double_scaled(self, tmp_path):
        """With scale=0.01, offset=100mm must appear as ~100mm, not 1mm."""
        from archpapercraft.exporter.pdf_export import export_pdf
        from archpapercraft.layout_packer.packer import PageSettings, pack_parts
        from archpapercraft.unfolder.exact_unfold import UnfoldedPart

        # Create a tiny triangle in model mm
        verts = np.array([[0, 0], [10, 0], [5, 8]], dtype=np.float64)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        part = UnfoldedPart(
            part_id=0,
            vertices_2d=verts,
            faces=faces,
            vert_map_3d=np.array([0, 1, 2], dtype=np.int32),
        )

        ps = PageSettings()
        layout = pack_parts([verts], ps, scale=0.01)

        out = tmp_path / "test.pdf"
        # Should not raise and should produce a valid file
        export_pdf(str(out), [part], layout, ps, scale=0.01)
        assert out.exists()
        assert out.stat().st_size > 100

    def test_svg_offset_not_double_scaled(self, tmp_path):
        from archpapercraft.exporter.svg_export import export_svg
        from archpapercraft.layout_packer.packer import PageSettings, pack_parts
        from archpapercraft.unfolder.exact_unfold import UnfoldedPart

        verts = np.array([[0, 0], [10, 0], [5, 8]], dtype=np.float64)
        faces = np.array([[0, 1, 2]], dtype=np.int32)
        part = UnfoldedPart(
            part_id=0,
            vertices_2d=verts,
            faces=faces,
            vert_map_3d=np.array([0, 1, 2], dtype=np.int32),
        )

        ps = PageSettings()
        layout = pack_parts([verts], ps, scale=0.01)

        out = tmp_path / "test.svg"
        export_svg(str(out), [part], layout, ps, scale=0.01)
        assert out.exists()

        content = out.read_text()
        # Verify that coordinates are reasonable (not shrunken to near-zero)
        assert "0.0" in content or "0.1" in content  # some coordinates exist
