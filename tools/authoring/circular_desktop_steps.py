"""Native C authoring from empty document. Observations never inject geometry."""

from __future__ import annotations

import copy
import math
import time
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox


def tab_area(radius, slope, width=.24, depth=9.5):
    """Independent local triangle minus oriented circular segment, paper mm²."""
    parameter = slope * width / (4 * radius)
    half_chord = width / (2 * (1 + parameter * parameter))
    sagitta = -slope * width * width / (8 * radius * (1 + parameter * parameter))
    if slope == 0:
        return half_chord * depth
    angle = 4 * math.atan(abs(parameter))
    # Stable theta-sin(theta), including the almost cylindrical fixture.
    segment = math.fsum((-1)**(n+1) * angle**(2*n+1) / math.factorial(2*n+1)
                        for n in range(1, 8))
    return half_chord * (depth-sagitta) - math.copysign(1, slope) * (radius/slope)**2 * segment/2


class CircularDesktopSteps:
    def _c_preview(self, dialog):
        self.click(dialog.compute)
        started = time.monotonic()
        while dialog._running is not None and time.monotonic()-started < 180:
            QTest.qWait(80)
        self.check(dialog._packet is not None, "C preview missing: " + dialog.feedback.text())
        self.log("actual_C_preview", status=dialog._packet["status"],
                 feedback=dialog.feedback.text(), elapsed_seconds=time.monotonic()-started)
        return dialog._packet

    def circular_case(self, name):
        self.data(self.w.units, 1)
        self.number(self.w.scale_field, 100)
        self.number(self.w.grid, 250)
        self.data(self.w.plane, "XY")
        self.data(self.w.curve_mode, "arc")
        self.shortcut(Qt.Key.Key_L)
        self.sketch_points(self.w.sketch, [
            [-1000, 0], [0, -1000], [1000, 0], [0, 1000], [-1000, 0],
        ])
        first_cap = self.w.selected_surface
        first = self.w.project.surfaces[first_cap].profile_id
        factor = 2 if name == "C-cone" else 1.000001 if name == "C-near" else 1
        depth = round(math.sqrt(800)*100, 6) if name == "C-cone" else 3000
        second = self._copy_loft_profile(first, factor=factor, depth=depth)
        owner = self._create_loft(first, second)
        receiver, rim, side = first_cap, "first", "inside"
        if name == "C-cone":
            # Remove only the redundant printed disk; its reusable source remains.
            self.select(first_cap)
            self.modal(lambda: self.action("delete_part"), self.ok)
            self.check(first in self.w.project.profiles, "Deleting a printed disk lost loft source")
            self.data(self.w.plane, "XY")
            self.data(self.w.curve_mode, "arc")
            self.shortcut(Qt.Key.Key_L)
            self.sketch_points(self.w.sketch, [
                [-2000, 0], [0, -2000], [2000, 0], [0, 2000], [-2000, 0],
            ])
            receiver = self.w.selected_surface
            self.transform(receiver, [0, 0, depth], [0, 0, 0])
            rim, side = "second", "outside"
        self.roles.update(circular_owner=owner, circular_receiver=receiver)
        self.select(owner)
        before = copy.deepcopy(self.w.project.to_dict())

        def cancel(dialog):
            self.click(dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))

        self.modal(lambda: self.action("curved_connector"), cancel)
        self.check(self.w.project.to_dict() == before, "C Cancel changed authored work")

        def edit(dialog):
            self.data(dialog.rim, rim)
            self.data(dialog.receiver, receiver)
            self.data(dialog.receiver_side, side)
            packet = self._c_preview(dialog)
            self.check(packet["status"] != "CERTIFIED_APPROXIMATE",
                       "Unknown paper thickness was falsely certified")
            self.check(not dialog.apply_button.isEnabled(),
                       "Unknown proof applied without intent choice")

            def material(widget):
                if not widget.known.isChecked():
                    self.click(widget.known)
                for key, value in (("thickness_mm", .2), ("clearance_mm", .01),
                                   ("bend_radius_mm", 0)):
                    self.number(widget.fields[key], value)
                self.ok(widget)

            self.modal(lambda: self.click(dialog.material_button), material)
            self.check(self.w.project.to_dict() == before, "Staged paper leaked into live project")
            self.data(dialog.receiver_side, "outside" if side == "inside" else "inside")
            self.check(self._c_preview(dialog)["status"] != "CERTIFIED_APPROXIMATE",
                       "Wrong receiver side was falsely certified")
            self.data(dialog.receiver_side, side)
            self.number(dialog.fields["nominal_base_mm"], 2)
            self.check(self._c_preview(dialog)["status"] != "CERTIFIED_APPROXIMATE",
                       "Wide tab exceeded declared deformation without refusal")
            self.number(dialog.fields["nominal_base_mm"], .24)
            self.click(dialog.tab_enabled)  # Explicitly omit slot0.
            self.combo(dialog.tabs, 1)
            self.number(dialog.tip, .01)
            packet = self._c_preview(dialog)
            self.check(packet["status"] == "CERTIFIED_APPROXIMATE", dialog.feedback.text())
            self.check(dialog.apply_button.isEnabled(), "Fresh C preview cannot apply")
            self.check(self.w.project.to_dict() == before, "Preview changed live source/cache")
            self.capture(name + "-actual-C-preview", dialog)
            self.click(dialog.apply_button)

        self.modal(lambda: self.action("curved_connector"), edit)
        self.check(len(self.w.project.curved_connectors) == 1, "C intent not created exactly once")
        cid = next(iter(self.w.project.curved_connectors))
        record = self.w.project.curved_connectors[cid]
        self.check(self.w.project.parts[self.w.project.part_for_surface(owner)].stale,
                   "Preview cache was injected instead of authored intent")
        authored = copy.deepcopy(self.w.project.to_dict())
        self.shortcut(Qt.Key.Key_Z)
        self.check(self.w.project.to_dict() == before, "One Undo did not revert material+intent")
        self.shortcut(Qt.Key.Key_Y)
        self.check(self.w.project.to_dict() == authored, "Redo lost C identity/draft")
        self.shortcut(Qt.Key.Key_R)
        self.check(self.w.project.curved_connector_status(cid)["status"] == "CERTIFIED_APPROXIMATE",
                   "Explicit recompute failed to certify actual source material")
        self.check(not record.tab_overrides[record.slot_ids[0]]["enabled"], "Omitted slot was lost")
        self.check(record.tab_overrides[record.slot_ids[1]]["tip_offset_mm"] == .01,
                   "Authored triangle tip was lost")
        self.circular_observation = dict(connector_id=cid, slot_ids=list(record.slot_ids),
                                         r0=10, r1=10*factor, height=depth*.01,
                                         rim=rim, receiver_side=side)
        self.add_page()
        self.place(receiver, 0, 40, 50)
        self.place(owner, 1, 55, 90, 17)
        self.paper_drag(owner, locked=False)
        self.place(owner, 1, 55, 90, 17)
        self.click(self.w.position_lock)
        self.click(self.w.rotation_lock)
        self.paper_drag(owner, locked=True)
        self.linked_pick()
        self.capture(name + "-authored-layout")
        self.step("C_actual_creation_repair_cancel_undo_source_and_layout",
                  fixture=name, **self.circular_observation)
        self.finish(name)

    def audit_circular_vectors(self, directory, svgs, pdf):
        from circular_svg_oracle import svg_signed_area
        from vector_curve_oracle import pdf_stroked_areas

        data = self.circular_observation
        record = self.w.project.curved_connectors[data["connector_id"]]
        self.check(record.slot_ids == data["slot_ids"], "Native reopen changed C slot UUIDs")
        r0, r1, height = data["r0"], data["r1"], data["height"]
        slant = math.hypot(r1-r0, height)
        body = math.pi * (r0+r1) * slant
        slope = (r0-r1)/slant * (1 if data["rim"] == "first" else -1)
        radius = r0 if data["rim"] == "first" else r1
        expected = body + 11*tab_area(radius, slope)
        own = self.w.project.part_for_surface(self.roles["circular_owner"])
        svg_area = None
        for svg in svgs:
            for group in ET.parse(svg).getroot():
                if group.get("data-part-id") != own:
                    continue
                by_role = {child.get("data-role"): child for child in group}
                loops = [float(abs(svg_signed_area(p.attrib["d"]))) for p in by_role["CUT"]]
                self.check(len(loops) == 1, "C CUT lost its single material union")
                self.check(len(by_role["TABS"]) == 11, "C output retained an omitted tab")
                svg_area = self.near(loops[0], expected, "C source/SVG material area",
                                     max(.01, 1e-6*body))
        self.check(svg_area is not None, "Actual C SVG material missing")
        pdf_areas = [value for page, value in pdf_stroked_areas(pdf) if page == 1]
        self.check(len(pdf_areas) == 1, "Actual C PDF has unexpected CUT material")
        self.near(pdf_areas[0], expected, "C source/PDF material area", max(.01, 1e-6*body))
        self.step("C_independent_source_and_actual_vector_material_area", source_body_mm2=body,
                  expected_union_mm2=expected, actual_pdf_union_mm2=pdf_areas[0],
                  source_native_strain="CERTIFIED_SEPARATELY_FROM_VECTOR_METRICS",
                  physical_build="NOT_RUN")
