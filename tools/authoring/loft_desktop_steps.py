"""Actual native input steps for B; no document or prepared geometry injection."""

from __future__ import annotations

import copy
import math
import time
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox


def simpson(function, low, high, count=8192):
    """Independent numerical integral, not a rigorous source certificate."""
    h = (high - low) / count
    return h / 3 * math.fsum(
        (1 if i in (0, count) else 4 if i % 2 else 2) * function(low + i * h)
        for i in range(count + 1)
    )


def expected_gothic_area():
    # Radius32.5, centers±12.5; scale1.2, normal depth10 paper mm.
    # Jacobian of S=(1-v)C+v(1.2C+d), integrated first over v.
    return 440 + 2 * 1.1 * 32.5 * simpson(
        lambda theta: math.sqrt(100 + .04 * (32.5 + 12.5 * math.cos(theta)) ** 2),
        math.atan2(30, -12.5), math.pi,
    )


def expected_bezier_area():
    # Own polynomial derivative of (0,0),(20,30),(60,30),(80,0).
    return 10 * simpson(lambda u: math.hypot(60 + 120*u - 120*u*u, 90 - 180*u), 0, 1)


class LoftDesktopSteps:
    def _copy_loft_profile(self, profile_id, *, factor, depth, origin=None):
        profile = self.w.project.profiles[profile_id]
        self.data(self.w.curve_choice, (profile_id, profile.segments[0].id))
        before = set(self.w.project.profiles)

        def edit(dialog):
            self.number(dialog.fields["factor"], factor)
            self.number(dialog.fields["depth"], depth)
            if origin:
                for key, value in zip(("origin_x", "origin_y", "origin_z"), origin):
                    self.number(dialog.fields[key], value)
            self.ok(dialog)

        self.modal(lambda: self.action("copy_profile"), edit)
        created = set(self.w.project.profiles) - before
        self.check(len(created) == 1, "UI copy did not create one independent source")
        return created.pop()

    def _create_loft(self, first, second, *, editing=False):
        before = set(self.w.project.surfaces)
        original = copy.deepcopy(self.w.project.to_dict())

        def edit(dialog):
            if not editing:
                self.data(dialog.first_profile, first)
                self.data(dialog.second_profile, second)
            if not dialog.confirm_pairs.isChecked():
                self.click(dialog.confirm_pairs)
            self.click(dialog.calculate)
            started = time.monotonic()
            while dialog._running_job is not None and time.monotonic() - started < 180:
                QTest.qWait(80)
            self.check(dialog.preview_result is not None, "Actual loft preview absent: "
                       + dialog.feedback.text())
            self.check(dialog.preview_result["status"] == "EXACT", dialog.feedback.text())
            self.check(self.w.project.to_dict() == original, "Preview changed the live document")
            self.check(dialog.apply_button.isEnabled(), "Current exact preview cannot be applied")
            self.capture("loft-actual-preview", dialog)
            self.step("actual_profile_pair_preview", first_profile_id=first,
                      second_profile_id=second, elapsed_seconds=time.monotonic()-started,
                      family=dialog.preview_result.get("family"),
                      authored_parameters=dialog._parameters_for_apply)
            self.click(dialog.apply_button)

        self.modal(lambda: self.action("edit_loft" if editing else "loft"), edit)
        if editing:
            self.check(set(self.w.project.surfaces) == before, "Edit duplicated the loft")
            return self.w.selected_surface
        created = set(self.w.project.surfaces) - before
        self.check(len(created) == 1, "UI loft did not create one surface")
        return created.pop()

    def loft_case(self, name):
        self.data(self.w.units, 1)
        self.number(self.w.scale_field, 100)
        self.number(self.w.grid, 250)
        wall = None
        if name == "loft-B1":
            wall = self.polygon("loft_wall", [
                [-6000, -2000], [6000, -2000], [6000, 8000], [-6000, 8000],
            ], plane="XZ")
            self.data(self.w.curve_mode, "arc")
            self.shortcut(Qt.Key.Key_H)
            self.sketch_points(self.w.sketch, [[-2000, 0], [-1750, 1250], [0, 3000]],
                               finish=False)
            self.sketch_points(self.w.sketch, [[1750, 1250], [2000, 0]], finish=False)
            self.data(self.w.curve_mode, "line")
            self.sketch_points(self.w.sketch, [[-2000, 0]])
            first = self.w.project.surfaces[wall].hole_profile_ids[0]
            second = self._copy_loft_profile(first, factor=1.2, depth=1000)
        elif name == "loft-B2":
            self.data(self.w.plane, "XY")
            self.data(self.w.curve_mode, "arc")
            self.shortcut(Qt.Key.Key_L)
            self.sketch_points(self.w.sketch, [
                [-2000, 0], [0, -2000], [2000, 0], [0, 2000], [-2000, 0],
            ])
            wall = self.w.selected_surface  # Authored disk remains a separate part.
            self.roles["loft_disk"] = wall
            first = self.w.project.surfaces[wall].profile_id
            second = self._copy_loft_profile(first, factor=1.2, depth=0)
        else:
            self.data(self.w.plane, "XY")
            self.data(self.w.curve_mode, "cubic")
            self.shortcut(Qt.Key.Key_L)
            self.sketch_points(self.w.sketch, [[0, 0], [2000, 3000], [6000, 3000], [8000, 0]],
                               finish=False)
            QTest.keyClick(self.w.sketch, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
            QTest.qWait(100)
            self.check(not self.w.sketch.drawing, "Open cubic did not become an authored profile")
            first = self.w.selected_profile
            second = self._copy_loft_profile(first, factor=1, depth=1000)
        loft = self._create_loft(first, second)
        self.roles["loft"] = loft
        self.check(self.w.project.surfaces[loft].kind ==
                   ("planar" if name == "loft-B2" else "ruled_loft"),
                   "B2 must be a real planar region; spatial loft cannot become a fake plane")
        self.shortcut(Qt.Key.Key_R)
        if wall:
            self.add_page()
            # Keep the circular disk's true curved material beyond the 10mm
            # print margin, including the independently reserved output bound.
            self.place(wall, 0, 30, 40)
            self.place(loft, 1, 40, 60, 17)
        else:
            self.place(loft, 0, 40, 60, 17)
        self.paper_drag(loft, locked=False)
        self.place(loft, 1 if wall else 0, 40, 60, 17)
        self.click(self.w.position_lock)
        self.click(self.w.rotation_lock)
        self.paper_drag(loft, locked=True)
        before = copy.deepcopy(self.w.project.to_dict())

        def cancel(dialog):
            self.click(dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))

        if name != "loft-B2":
            self.modal(lambda: self.action("edit_loft"), cancel)
            self.check(self.w.project.to_dict() == before, "Cancel changed loft/frame/layout")
            self._create_loft(first, second, editing=True)
            self.shortcut(Qt.Key.Key_R)
        self.linked_pick()
        self.capture(name + "-authored-layout")
        self.finish(name)

    def audit_loft_vectors(self, name, directory, svgs, pdf):
        from vector_curve_oracle import pdf_stroked_areas, svg_signed_area

        sid = self.roles["loft"]
        expected = (expected_gothic_area() if name == "loft-B1" else
                    math.pi * (24**2 - 20**2) if name == "loft-B2" else
                    expected_bezier_area())
        all_svg_loops, observations = [], []
        for svg in svgs:
            for group in ET.parse(svg).getroot():
                if "data-part-id" not in group.attrib:
                    continue
                cut = next(node for node in group if node.get("data-role") == "CUT")
                loops = [abs(svg_signed_area(node.attrib["d"])) for node in cut]
                all_svg_loops.extend(loops)
                if group.attrib["data-part-id"] == self.w.project.surfaces[sid].part_id:
                    net = max(loops) - (sum(loops)-max(loops))
                    observations.append(self.near(net, expected, "actual loft SVG area",
                                                  max(.01, 1e-6*expected)))
                    if name == "loft-B1":
                        self.check(any("C " in node.attrib["d"] for node in cut),
                                   "Gothic loft native boundaries became a chord mesh")
                    if name == "loft-B2":
                        self.check(len(loops) == 2, "Coplanar band lost its actual cut hole")
        pdf_loops = sorted(value for _, value in pdf_stroked_areas(pdf))
        self.check(len(pdf_loops) == len(all_svg_loops), "PDF CUT coverage mismatch")
        for actual, reference in zip(pdf_loops, sorted(all_svg_loops)):
            observations.append(self.near(actual, reference, "actual SVG/PDF CUT loop area",
                                          max(.01, 1e-6*reference)))
        if name != "loft-B2":
            # The loft is the only part on its page; the other page contains wall/hole.
            page = 1 if name == "loft-B1" else 0
            own = [value for index, value in pdf_stroked_areas(pdf) if index == page]
            self.check(len(own) == 1, "Loft page has unexpected extra CUT material")
            observations.append(self.near(own[0], expected, "actual source/PDF loft area",
                                          max(.01, 1e-6*expected)))
        self.step("actual_loft_independent_vector_oracles", fixture=name,
                  observations=observations, source_numeric_oracle="independent Simpson integral",
                  source_interval_certificate="separately reviewed production intrinsic bound",
                  preset_used=False, physical_build="NOT_RUN", novice_participants=0)
