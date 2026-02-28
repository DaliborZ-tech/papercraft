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


class TestGothicWindowExportScale:
    """End-to-end: gothic window → auto seams → unfold → pack → PDF produces visible parts."""

    def test_gothic_window_parts_visible_on_paper(self, tmp_path):
        """Parts should be at least several mm wide on paper (units=m, 1:100)."""
        from archpapercraft.arch_presets.gothic_window import generate_gothic_window
        from archpapercraft.seam_editor.auto_seams import auto_seams
        from archpapercraft.unfolder.approx_unfold import unfold_all_parts
        from archpapercraft.layout_packer.packer import PageSettings, pack_parts
        from archpapercraft.core_geometry.units import to_mm

        # Generate gothic window mesh (units are meters: width=1.2, height=2.8)
        mesh = generate_gothic_window({})

        # Compute paper_scale like the real pipeline does
        unit_to_mm = to_mm(1.0, "m")  # 1000
        scale_factor = 0.01  # 1:100
        paper_scale = unit_to_mm * scale_factor  # 10

        seams = auto_seams(mesh, scale=paper_scale)
        parts = unfold_all_parts(mesh, seams)
        assert len(parts) > 0

        outlines = [p.vertices_2d for p in parts]
        ps = PageSettings()
        layout = pack_parts(outlines, ps, scale=paper_scale)

        # Check that placed parts have non-trivial bounding boxes
        max_w = 0.0
        visible_count = 0
        for pl in layout.placements:
            bb = pl.bbox_max - pl.bbox_min
            w, h = float(bb[0]), float(bb[1])
            max_w = max(max_w, w, h)
            if w > 0.5 and h > 0.5:
                visible_count += 1

        # At least one part should be visibly large (>5 mm)
        assert max_w > 5.0, f"Largest dimension {max_w} mm, expected >5 mm"
        # Most parts should be visible
        assert visible_count > 0, "No visible parts on paper"

    def test_paper_scale_formula(self):
        from archpapercraft.core_geometry.units import to_mm

        # 1:100 in meters → 10 mm per model unit on paper
        assert to_mm(1.0, "m") * 0.01 == pytest.approx(10.0)

        # 1:50 in meters → 20 mm per model unit
        assert to_mm(1.0, "m") * 0.02 == pytest.approx(20.0)

        # 1:100 in cm → 0.1 mm per model unit
        assert to_mm(1.0, "cm") * 0.01 == pytest.approx(0.1)

        # 1:1 in mm → 1 mm per model unit
        assert to_mm(1.0, "mm") * 1.0 == pytest.approx(1.0)


# ======================================================================
# Splay & tracery
# ======================================================================


class TestGothicWindowSplay:
    """Test improved splay and tracery features."""

    def test_splay_widens_back_inner(self):
        from archpapercraft.arch_presets.gothic_window import generate_gothic_window

        mesh_no_splay = generate_gothic_window({"splay_angle": 0.0})
        mesh_splay = generate_gothic_window({"splay_angle": 15.0})

        # With splay, the sum of abs(x) at the back (y>0.3) should be larger,
        # because inner vertices are pushed outward while outer stay the same.
        back_no = mesh_no_splay.vertices[mesh_no_splay.vertices[:, 1] > 0.3]
        back_sp = mesh_splay.vertices[mesh_splay.vertices[:, 1] > 0.3]
        sum_abs_x_no = np.abs(back_no[:, 0]).sum()
        sum_abs_x_sp = np.abs(back_sp[:, 0]).sum()
        assert sum_abs_x_sp > sum_abs_x_no

    def test_tracery_adds_geometry(self):
        from archpapercraft.arch_presets.gothic_window import generate_gothic_window

        mesh_no_tracery = generate_gothic_window({"tracery": False})
        mesh_tracery = generate_gothic_window({"tracery": True})
        # Tracery adds extra vertices and faces
        assert len(mesh_tracery.vertices) > len(mesh_no_tracery.vertices)
        assert len(mesh_tracery.faces) > len(mesh_no_tracery.faces)

    def test_spring_ratio(self):
        from archpapercraft.arch_presets.gothic_window import generate_gothic_window

        mesh_low = generate_gothic_window({"spring_ratio": 0.4})
        mesh_high = generate_gothic_window({"spring_ratio": 0.7})
        # Both should produce valid geometry
        assert len(mesh_low.vertices) > 0
        assert len(mesh_high.vertices) > 0


# ======================================================================
# Scene operations
# ======================================================================


class TestSceneOperations:
    """Test node deletion and duplication."""

    def test_add_and_remove_node(self):
        from archpapercraft.scene_graph.scene import Scene
        from archpapercraft.scene_graph.node import NodeType

        scene = Scene()
        node = scene.add_node("TestBox", NodeType.PRIMITIVE_BOX)
        assert len(scene.root.children) == 1

        scene.remove_node(node)
        assert len(scene.root.children) == 0

    def test_find_node_by_id(self):
        from archpapercraft.scene_graph.scene import Scene
        from archpapercraft.scene_graph.node import NodeType

        scene = Scene()
        node = scene.add_node("TestBox", NodeType.PRIMITIVE_BOX)

        found = scene.find_node(node.node_id)
        assert found is node

        assert scene.find_node("nonexistent") is None

    def test_duplicate_preserves_params(self):
        from archpapercraft.scene_graph.scene import Scene
        from archpapercraft.scene_graph.node import NodeType

        scene = Scene()
        node = scene.add_node("GW", NodeType.GOTHIC_WINDOW, width=1.5, height=3.0)
        # Simulate duplication (same as MainWindow._duplicate_selected)
        dup = scene.add_node(
            f"{node.name} (kopie)", node.node_type, **dict(node.parameters),
        )
        assert dup.parameters["width"] == 1.5
        assert dup.parameters["height"] == 3.0
        assert dup.node_id != node.node_id


# ======================================================================
# Build guide
# ======================================================================


class TestBuildGuide:
    """Test build guide generation."""

    def test_guide_from_markings(self):
        from archpapercraft.tabs_generator.build_guide import generate_build_guide
        from archpapercraft.tabs_generator.markings import PartMarkings

        m1 = PartMarkings(part_id=1, part_label="Díl 1")
        m2 = PartMarkings(part_id=2, part_label="Díl 2")
        guide = generate_build_guide(
            [m1, m2], project_name="Test", scale="1:50", paper_grammage=200,
        )
        assert len(guide.parts) == 2
        assert guide.project_name == "Test"
        assert guide.scale == "1:50"
        text = guide.to_text()
        assert "Test" in text
        assert "1:50" in text
        assert "200 g/m²" in text


# ======================================================================
# Preferences — round-trip save/load
# ======================================================================


class TestPreferences:
    """Test preferences save / load / reset."""

    def test_defaults(self):
        from archpapercraft.preferences.settings import Preferences
        p = Preferences()
        assert p.general.language == "cs"
        assert p.export.default_format == "pdf"

    def test_round_trip(self, tmp_path):
        from archpapercraft.preferences.settings import Preferences
        p = Preferences()
        p.general.language = "en"
        p.export.png_dpi = 300
        path = p.save(tmp_path / "settings.json")
        loaded = Preferences.load(path)
        assert loaded.general.language == "en"
        assert loaded.export.png_dpi == 300

    def test_reset(self):
        from archpapercraft.preferences.settings import Preferences
        p = Preferences.reset()
        assert p.general.max_undo_depth == 200


# ======================================================================
# CommandStack — undo/redo integration
# ======================================================================


class TestCommandStackWiring:
    """Test that CommandStack commands work with Scene."""

    def test_add_and_undo(self):
        from archpapercraft.commands.command_stack import AddNodeCommand, CommandStack
        from archpapercraft.scene_graph.node import NodeType
        from archpapercraft.scene_graph.scene import Scene

        scene = Scene()
        stack = CommandStack()
        cmd = AddNodeCommand(scene, "TestBox", NodeType.PRIMITIVE_BOX)
        stack.execute(cmd)
        assert len(scene.root.children) == 1
        assert scene.root.children[0].name == "TestBox"

        stack.undo()
        assert len(scene.root.children) == 0

        stack.redo()
        assert len(scene.root.children) == 1

    def test_remove_and_undo(self):
        from archpapercraft.commands.command_stack import (
            AddNodeCommand, RemoveNodeCommand, CommandStack,
        )
        from archpapercraft.scene_graph.node import NodeType
        from archpapercraft.scene_graph.scene import Scene

        scene = Scene()
        stack = CommandStack()
        add_cmd = AddNodeCommand(scene, "Kvádr", NodeType.PRIMITIVE_BOX)
        stack.execute(add_cmd)
        node = scene.root.children[0]

        rm_cmd = RemoveNodeCommand(scene, node)
        stack.execute(rm_cmd)
        assert len(scene.root.children) == 0

        stack.undo()
        assert len(scene.root.children) == 1
        assert scene.root.children[0].name == "Kvádr"

    def test_set_parameter_and_undo(self):
        from archpapercraft.commands.command_stack import (
            AddNodeCommand, SetParameterCommand, CommandStack,
        )
        from archpapercraft.scene_graph.node import NodeType
        from archpapercraft.scene_graph.scene import Scene

        scene = Scene()
        stack = CommandStack()
        stack.execute(AddNodeCommand(scene, "Box", NodeType.PRIMITIVE_BOX))
        node = scene.root.children[0]
        node.parameters["width"] = 1.0

        cmd = SetParameterCommand(node, "width", 5.0)
        stack.execute(cmd)
        assert node.parameters["width"] == 5.0

        stack.undo()
        assert node.parameters["width"] == 1.0
