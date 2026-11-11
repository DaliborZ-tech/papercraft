"""Actual LINE subdivision of a joined architectural part and interior trace.

This driver only observes the project. All authored changes use real widgets.
It proves a narrow LINE slice, not curved trim/loft remapping or a new user.
"""

from __future__ import annotations

import copy
import math
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox


class SubdivisionDesktopSteps:
    def audit_subdivision_vectors(self, directory, svgs, pdf):
        from desktop_b_proof import area, pdf_stroked_loops, svg_line_loops

        p = self.w.project
        body_id = p.surfaces[self.roles["AU13_wall"]].part_id
        base_id = p.surfaces[self.roles["AU13_base"]].part_id
        # Independent source lengths/areas, including the existing authored
        # single trapezoid: b=90mm, depth=2mm, taper=.6 gives144mm2.
        expected = {body_id: 4000+100*math.hypot(30, 35)+144, base_id: 13000}
        source_areas = {}
        for part_id, target in expected.items():
            group = next(g for svg in svgs for g in ET.parse(svg).getroot().iter()
                         if g.attrib.get("data-part-id") == part_id)
            cuts = next(g for g in group if g.attrib.get("data-role") == "CUT")
            loops = [loop for path in cuts for loop in svg_line_loops(path.attrib["d"])]
            actual = sum(area(loop) for loop in loops)
            self.near(actual, target, "AU13 actual SVG material area", .01)
            source_areas[part_id] = {"expected": target, "svg": actual}
        actual_pdf = pdf_stroked_loops(pdf)
        for page_index, part_id in ((0, base_id), (1, body_id)):
            matches = [loop for index, loop in actual_pdf if index == page_index
                       and abs(area(loop)-expected[part_id]) <= .01]
            self.check(len(matches) == 1,
                       "PDF omitted/duplicated actual material after subdivision")
            source_areas[part_id]["pdf"] = area(matches[0])
        self.step("AU13_native_SVG_PDF_direct_source_material_areas", areas=source_areas,
                  snapshot=str(directory / "snapshot.json"), mode="EXACT_LINE_SLICE")

    def split_line(self, sid, index, distance, *, cancel=False):
        self.select(sid)
        profile = self.w.project.profiles[self.w.project.surfaces[sid].profile_id]
        edge_id = profile.segments[index].id
        self.data(self.w.curve_choice, (profile.id, edge_id))
        before = copy.deepcopy(self.w.project.to_dict())
        vertices = {vertex.id for vertex in profile.vertices}
        segments = {edge.id for edge in profile.segments}

        def edit(dialog):
            self.visible(dialog.distance).setFocus()
            QTest.keyClick(dialog.distance, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
            QTest.keyClicks(dialog.distance, str(distance))
            self.capture("AU13-split-preview", dialog)
            self.click(dialog.buttons.button(
                QDialogButtonBox.StandardButton.Cancel if cancel else
                QDialogButtonBox.StandardButton.Ok))

        self.modal(lambda: self.action("split_profile"), edit)
        if cancel:
            self.check(self.w.project.to_dict() == before, "Canceled split changed model/layout")
            return None
        current = self.w.project.profiles[profile.id]
        new_vertices = [v.id for v in current.vertices if v.id not in vertices]
        new_segments = [s.id for s in current.segments if s.id not in segments]
        self.check(len(new_vertices) == 1 and len(new_segments) == 2,
                   "Actual subdivision did not create one point/two source segments")
        self.check(self.w.selected_vertex == (profile.id, new_vertices[0]) and
                   self.w.selected_edge[0] == sid,
                   "Subdivision context did not select the new source point/edge")
        self.check(self.w.project.parts[self.w.project.surfaces[sid].part_id].stale,
                   "Subdivision did not stale the whole owning material part")
        self.step("AU13_actual_typed_distance_without_Enter", source_profile=profile.id,
                  original_edge=edge_id, created_vertex=new_vertices[0],
                  created_edges=new_segments, distance_model_mm=distance)
        return new_segments

    def subdivision_case(self):
        self.data(self.w.units, 1)
        wall = self.rectangle("AU13_wall", 10000, 4000, "XZ")
        roof = self.rectangle("AU13_roof", 10000, math.hypot(3000, 3000),
                              position=[0, 0, 4000], rotation=[45, 0, 0])
        joint_id = self.fold(wall, 2, roof, 0, 45)
        base = self.rectangle("AU13_base", 13000, 10000, position=[-1500, -2000, 0])
        attachment_id = self.attach(wall, 0, base)
        connector_id = self.tab(wall, attachment_id, width=2)
        self.shortcut(Qt.Key.Key_R)
        self.add_page()
        self.place(base, 0, 30, 30)
        self.place(wall, 1, 60, 60, 30)
        self.click(self.w.position_lock)
        self.click(self.w.rotation_lock)
        project = self.w.project
        pid = project.surfaces[wall].part_id
        profile_id = project.surfaces[wall].profile_id
        original_vertices = [v.id for v in project.profiles[profile_id].vertices]
        original_frame = copy.deepcopy(project.parts[pid].frame)
        original_place = copy.deepcopy(project.placements[pid])
        original_joint = copy.deepcopy(project.joints[joint_id])
        original_attachment = copy.deepcopy(project.attachments[attachment_id])
        original_connector = copy.deepcopy(project.connectors[connector_id])
        reference = self.wall_page_points(wall)
        expected_wall = [
            [60+x*math.cos(math.pi/6)-y*math.sin(math.pi/6),
             60+x*math.sin(math.pi/6)+y*math.cos(math.pi/6)]
            for x, y in [(0, 0), (100, 0), (100, 40), (0, 40)]
        ]

        def invariant(label):
            p = self.w.project
            self.check(p.parts[pid].frame == original_frame and p.placements[pid] == original_place,
                       label+": stable frame/page2/[60,60]/30deg/both locks changed")
            self.check(p.joints[joint_id] == original_joint and
                       p.attachments[attachment_id] == original_attachment and
                       p.connectors[connector_id] == original_connector,
                       label+": join/trace/connector IDs or authored overrides changed")
            profile = p.profiles[profile_id]
            points = self.wall_page_points(wall)
            for vertex_id, expected in zip(original_vertices, expected_wall):
                index = next(i for i, vertex in enumerate(profile.vertices)
                             if vertex.id == vertex_id)
                self.check(math.dist(points[index], expected) <= 1e-10,
                           label+": an original root-wall point moved")

        self.split_line(wall, 0, 3000, cancel=True)
        children = self.split_line(wall, 0, 3000)
        changed = copy.deepcopy(self.w.project.to_dict())
        self.shortcut(Qt.Key.Key_Z)
        self.check(self.w.project.parts[pid].frame == original_frame and
                   len(self.w.project.profiles[profile_id].vertices) == 4,
                   "Actual split Undo lost original source")
        self.shortcut(Qt.Key.Key_Y)
        self.check(self.w.project.to_dict() == changed,
                   "Actual split Redo changed child identities or source")
        self.shortcut(Qt.Key.Key_R)
        invariant("axis split")
        self.select(wall)
        self.data(self.w.curve_choice, (profile_id, children[0]))

        def merge(dialog):
            self.check(len(dialog.choices.selectedItems()) == 2,
                       "Inverse merge did not expose both source descendants")
            self.capture("AU13-inverse-merge-preview", dialog)
            self.ok(dialog)

        self.modal(lambda: self.action("merge_profile"), merge)
        self.shortcut(Qt.Key.Key_R)
        invariant("inverse merge with retired semantic axis")
        self.split_line(wall, 2, 2500)  # Actually joined wall/roof hinge.
        self.shortcut(Qt.Key.Key_R)
        invariant("joined hinge split")
        self.split_line(wall, 0, 6000)  # Interior base trace + authored tab owner.
        self.shortcut(Qt.Key.Key_R)
        invariant("interior trace source split")
        self.capture("AU13-split-joined-hinge-and-interior-trace")

        # The unedited root wall remains fixed when the other surface changes.
        slope = math.hypot(3000, 3500)
        self.vertex(roof, 2, y=slope)
        self.vertex(roof, 3, y=slope)
        self.number(self.w.transform_fields[3], math.degrees(math.atan2(3500, 3000)))
        self.check(self.w.project.parts[pid].stale, "Edited roof did not stale whole mixed part")
        self.shortcut(Qt.Key.Key_R)
        invariant("roof rise3000 to3500")
        self.paper_drag(wall, locked=True)
        self.linked_pick()
        self.capture("AU13-final-manual-layout")
        self.step("AU13_LINE_semantic_axis_join_trace_and_mixed_change",
                  original_wall_points=reference, final_wall_points=self.wall_page_points(wall),
                  source_profile_id=profile_id, part_id=pid,
                  joint_id=joint_id, attachment_id=attachment_id, connector_id=connector_id,
                  limitations="LINE only; curved trim and loft parameter remapping not proved")
        self.finish("AU13-line")
