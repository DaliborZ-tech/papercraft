"""Intentionally red P0 regressions; run explicitly, outside the legacy testpaths.

No xfail or broad exception suppression: unrelated failures remain visible.
These are product expectations, not assertions that a broken implementation stays broken.
"""
import math
import xml.etree.ElementTree as ET

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.project_io.project import Project
from archpapercraft.scene_graph.node import NodeType
from archpapercraft.tabs_generator.tabs import TabSettings, generate_tabs_for_part
from archpapercraft.unfolder.exact_unfold import unfold_part
from archpapercraft.unfolder.strategies import generate_rings


def test_parent_transform_applies_to_export_geometry():
    scene = Project().scene
    parent = scene.add_node('parent', NodeType.GROUP)
    parent.transform.position[:] = [100, 0, 0]
    scene.add_node('child', NodeType.PRIMITIVE_BOX, parent=parent, dx=10, dy=10, dz=10)
    scene.rebuild_meshes()
    assert np.mean(scene.collect_visible_meshes(True)[0].vertices[:,0]) == 100


def test_future_schema_is_rejected_or_preserved():
    # Either explicit refusal or full retention is acceptable; current writer silently downgrades.
    data = {'version': '999.0', 'future_payload': {'must_preserve': True}}
    try:
        project = Project.from_dict(data)
    except ValueError as exc:
        assert 'schema' in str(exc).lower() or 'version' in str(exc).lower()
        return
    assert project.to_dict()['version'] == '999.0'
    assert project.to_dict()['future_payload'] == data['future_payload']


def test_open_panel_has_four_boundary_cuts():
    mesh = MeshData(np.array([[0.,0,0],[20,0,0],[20,10,0],[0,10,0]]), np.array([[0,1,2],[0,2,3]]))
    result = unfold_part(mesh,[0,1])
    assert len(result.cut_edges) == 4


def test_cone_band_joining_side_is_slant_height():
    polygon = generate_rings(np.array([[10.,0.],[20.,math.sqrt(800.)]]),num_rings=1)[0]
    assert abs(np.linalg.norm(polygon[2]-polygon[1])-30.) <= 0.01


def test_two_separate_parts_have_one_tab_per_joint():
    vertices = np.array([[0.,0.],[20.,0.],[20.,10.],[0.,10.]])
    first = generate_tabs_for_part(vertices,[(0,1)],{(0,1):7},TabSettings())
    second = generate_tabs_for_part(vertices,[(0,1)],{(0,1):7},TabSettings())
    assert len(first)+len(second) == 1


def test_svg_honors_rotation_and_landscape(tmp_path):
    from archpapercraft.exporter.svg_export import export_svg
    from archpapercraft.layout_packer.packer import LayoutResult, Orientation, PageSettings, PartRotation, PlacedPart
    from archpapercraft.unfolder.exact_unfold import UnfoldedPart
    vertices = np.array([[0.,0.],[100.,0.],[100.,40.],[0.,40.]])
    part = UnfoldedPart(0,vertices,np.array([[0,1,2],[0,2,3]]),np.arange(4),cut_edges=[(0,1),(1,2),(2,3),(3,0)])
    layout = LayoutResult(1,[PlacedPart(0,0,np.zeros(2),rotation=PartRotation.DEG_90)])
    target = tmp_path/'page.svg'
    export_svg(target,[part],layout,PageSettings(orientation=Orientation.LANDSCAPE))
    root = ET.parse(target).getroot()
    assert root.attrib['width'] == '297.0mm'
    # Rotation is separately measured by integration_probe; no implementation-derived expected geometry.
