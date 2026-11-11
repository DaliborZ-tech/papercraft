"""Real D widget input; only observations read the live construction document."""

from __future__ import annotations

import copy
import math
import time
import xml.etree.ElementTree as ET
from fractions import Fraction

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox


def source_point(u, v):
    """Independent paper-mm target S=(40u,20uv,30v), no application imports."""
    return [40 * u, 20 * u * v, 30 * v]


def triangle_area(points):
    a, b, c = points
    x, y = [[point[i] - a[i] for i in range(3)] for point in (b, c)]
    return (
        math.sqrt(
            sum(
                value * value
                for value in (
                    x[1] * y[2] - x[2] * y[1],
                    x[2] * y[0] - x[0] * y[2],
                    x[0] * y[1] - x[1] * y[0],
                )
            )
        )
        / 2
    )


def profile_point(profile, segment_id, parameter):
    """Independent analytic source reader; no production curve/mesh evaluator."""
    segment = next(s for s in profile.segments if s.id == segment_id)
    a = next(v.point for v in profile.vertices if v.id == segment.start_vertex_id)
    b = next(v.point for v in profile.vertices if v.id == segment.end_vertex_id)
    if segment.kind == "line":
        point = [(1 - parameter) * x + parameter * y for x, y in zip(a, b)]
    elif segment.kind == "arc":
        center = segment.data["center"]
        angle = math.radians(segment.data["sweep_deg"]) * parameter
        c, s = math.cos(angle), math.sin(angle)
        x, y = a[0] - center[0], a[1] - center[1]
        point = [center[0] + x * c - y * s, center[1] + x * s + y * c]
    else:
        raise AssertionError("This independent gothic oracle supports only native L/A sources")
    return [
        (profile.plane.origin[i] + profile.plane.u[i] * point[0] + profile.plane.v[i] * point[1])
        * 0.01
        for i in range(3)
    ]


def profile_area(profile):
    """Independent line/circle Green integral in this fixture's model plane."""
    terms = []
    for segment in profile.segments:
        a = next(v.point for v in profile.vertices if v.id == segment.start_vertex_id)
        b = next(v.point for v in profile.vertices if v.id == segment.end_vertex_id)
        if segment.kind == "line":
            terms.append((a[0] * b[1] - a[1] * b[0]) / 2)
        elif segment.kind == "arc":
            cx, cy = segment.data["center"]
            radius2 = (a[0] - cx) ** 2 + (a[1] - cy) ** 2
            terms.append(
                (
                    cx * (b[1] - a[1])
                    - cy * (b[0] - a[0])
                    + radius2 * math.radians(segment.data["sweep_deg"])
                )
                / 2
            )
        else:
            raise AssertionError("Unsupported source for independent profile area")
    return abs(math.fsum(terms)) * 0.01**2


class SegmentationDesktopSteps:
    def _gothic_segmentation_sources(self):
        self.number(self.w.grid, 50)
        front = self.polygon(
            "D_front_wall",
            [
                [-6000, -2000],
                [6000, -2000],
                [6000, 8000],
                [-6000, 8000],
            ],
            plane="XY",
        )

        def hole(wall, half_width, height, via_x):
            self.select(wall)
            self.data(self.w.curve_mode, "arc")
            self.shortcut(Qt.Key.Key_H)
            self.sketch_points(
                self.w.sketch, [[-half_width, 0], [-via_x, 1250], [0, height]], finish=False
            )
            self.sketch_points(self.w.sketch, [[via_x, 1250], [half_width, 0]], finish=False)
            self.data(self.w.curve_mode, "line")
            self.sketch_points(self.w.sketch, [[-half_width, 0]])
            pid = self.w.project.surfaces[wall].hole_profile_ids[0]
            profile = self.w.project.profiles[pid]
            self.check(
                len(profile.vertices) == 3 and len(profile.segments) == 3,
                "Independent native gothic hole lost its sharp corner",
            )
            for vertex, (x, y) in zip(
                profile.vertices, [(-half_width, 0), (0, height), (half_width, 0)]
            ):
                self.data(self.w.vertex_choice, (pid, vertex.id))
                self.number(self.w.vertex_x, x)
                self.number(self.w.vertex_y, y)
            # Real mouse drawing is followed by real numeric curve editing.
            angle = -math.degrees(2 * math.atan2(half_width, height))
            for segment in profile.segments[:2]:
                self.data(self.w.curve_choice, (pid, segment.id))

                def edit(dialog):
                    if not dialog.details.isChecked():
                        self.click(dialog.details)
                    self.number(dialog.fields["angle"], angle)
                    self.ok(dialog)

                self.modal(lambda: self.action("edit_curve"), edit)
            return pid

        first = hole(front, 2000, 3000, 1750)
        # The back wall's source plane is at depth10mm. Its hole is newly DRAWN
        # there, not a homothetic copy of the first hole.
        outer = self.w.project.surfaces[front].profile_id
        back_profile = self._copy_loft_profile(outer, factor=1, depth=1000)
        self.action("profile_surface")
        back = self.w.selected_surface
        self.check(
            back != front and self.w.project.surfaces[back].profile_id == back_profile,
            "Actual source-profile surface command failed",
        )
        self.roles["D_back_wall"] = back
        second = hole(back, 1800, 2500, 1500)
        self.shortcut(Qt.Key.Key_R)
        self.step(
            "B3_independently_drawn_gothic_profiles",
            first_profile_id=first,
            second_profile_id=second,
            first_dimensions_paper_mm=[40, 30],
            second_dimensions_paper_mm=[36, 25],
            depth_paper_mm=10,
            method="own native arc+line holes; actual numeric endpoint/angle editing",
        )
        return first, second, self.w.project.profiles[second].vertices[1].id

    def _wait_segment_preview(self, dialog):
        self.click(dialog.preview_button)
        started = time.monotonic()
        while dialog._running is not None and time.monotonic() - started < 120:
            QTest.qWait(80)
        self.check(
            dialog._running is None, "Segment preview did not finish within bounded deadline"
        )
        return time.monotonic() - started

    def _manual_segment_half(self, vid, page_index, first, count):
        records = self.w.project.segmented_variants[vid].triangle_bindings
        self.select(records[0]["surface_id"])
        before = copy.deepcopy(self.w.project.to_dict())

        def edit(dialog):
            self.check(
                dialog.page.currentData() is None and not dialog.parts.selectedItems(),
                "Grid inferred a page or preselected material",
            )
            item = dialog.parts.item(first)
            dialog.parts.scrollToItem(item)
            QTest.mouseClick(
                dialog.parts.viewport(),
                Qt.MouseButton.LeftButton,
                pos=dialog.parts.visualItemRect(item).center(),
            )
            for _ in range(count - 1):
                QTest.keyClick(dialog.parts, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
            chosen = [i.data(Qt.ItemDataRole.UserRole) for i in dialog.parts.selectedItems()]
            expected = [r["part_id"] for r in records[first : first + count]]
            self.check(
                chosen == expected, "Actual list range selection changed part identity/order"
            )
            self.data(dialog.page, self.w.project.pages[page_index].id)
            self.number(dialog.columns, 8)
            for field, value in (
                (dialog.x, 25),
                (dialog.y, 25),
                (dialog.pitch_x, 18),
                (dialog.pitch_y, 22),
            ):
                self.number(field, value)
            self.click(dialog.preview_button)
            self.check(dialog._preview_updates is not None, dialog.feedback.text())
            self.check(self.w.project.to_dict() == before, "Grid preview moved live material")
            self.capture(f"D-manual-page{page_index + 1}", dialog)
            self.ok(dialog)

        self.modal(lambda: self.action("manual_grid"), edit)
        for index, record in enumerate(records[first : first + count]):
            place = self.w.project.placements[record["part_id"]]
            self.check(
                [place.page_id, place.x_mm, place.y_mm, place.rotation_deg]
                == [
                    self.w.project.pages[page_index].id,
                    25 + (index % 8) * 18,
                    25 + (index // 8) * 22,
                    0,
                ],
                "Explicit grid placement did not survive command",
            )
        self.step(
            "D_explicit_manual_grid",
            page=page_index + 1,
            first=first,
            count=count,
            columns=8,
            origin_paper_mm=[25, 25],
            pitch_paper_mm=[18, 22],
            angle_deg=0,
        )

    def segmentation_case(self, *, gothic=False):
        self.data(self.w.units, 1)
        self.number(self.w.scale_field, 100)
        self.number(self.w.grid, 250)
        self.data(self.w.plane, "XY")
        if gothic:
            first, second, vertex = self._gothic_segmentation_sources()
        else:
            self.data(self.w.curve_mode, "line")
            self.shortcut(Qt.Key.Key_L)
            self.sketch_points(self.w.sketch, [[0, 0], [4000, 0]], finish=False)
            QTest.keyClick(self.w.sketch, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
            QTest.qWait(100)
            first = self.w.selected_profile
            self.check(
                first is not None and not self.w.project.surfaces,
                "Own open line profile became a filled preset",
            )
            second = self._copy_loft_profile(first, factor=1, depth=3000)
            vertex = self.w.project.profiles[second].vertices[1].id
            self.data(self.w.vertex_choice, (second, vertex))
            self.number(self.w.vertex_y, 2000)
        before = copy.deepcopy(self.w.project.to_dict())
        surfaces = set(self.w.project.surfaces)

        def target(dialog):
            self.data(dialog.first_profile, first)
            self.data(dialog.second_profile, second)
            self.click(dialog.confirm_pairs)
            self.click(dialog.calculate)
            started = time.monotonic()
            while dialog._running_job is not None and time.monotonic() - started < 120:
                QTest.qWait(80)
            self.check(dialog.preview_result is not None, dialog.feedback.text())
            self.check(dialog.preview_result["status"] == "REJECTED", dialog.feedback.text())
            self.check(
                not dialog.apply_button.isEnabled(), "Nondevelopable smooth target got EXACT"
            )
            self.check(self.w.project.to_dict() == before, "Rejected preview mutated source")
            self.capture("D-rejected-exact-target", dialog)
            self.click(dialog.keep_target)
            self.check(
                dialog.apply_button.isEnabled(), "Cannot explicitly retain construction target"
            )
            self.click(dialog.apply_button)

        self.modal(lambda: self.action("loft"), target)
        created = set(self.w.project.surfaces) - surfaces
        self.check(len(created) == 1, "Target creation lost or duplicated source")
        sid = created.pop()
        self.roles["D_target"] = sid
        self.select(sid)
        source_state = copy.deepcopy(self.w.project.to_dict())

        def strict(dialog):
            self.number(dialog.deviation, 0.000001)
            self.number(dialog.cells, 1)
            elapsed = self._wait_segment_preview(dialog)
            self.check(dialog._preview is None, "Impossible budget produced a confirmable variant")
            self.check(
                not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled(),
                "Hard-budget failure enabled confirmation",
            )
            self.check(
                self.w.project.to_dict() == source_state, "Failed segmentation changed target"
            )
            self.capture("D-hard-budget-rejected", dialog)
            self.step(
                "D_stricter_unsatisfied_budget_blocks_confirmation",
                budget_paper_mm=0.000001,
                max_cells=1,
                feedback=dialog.feedback.text(),
                elapsed_seconds=elapsed,
            )
            self.click(dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel))

        self.modal(lambda: self.action("segment"), strict)

        def approximate(dialog):
            elapsed = self._wait_segment_preview(dialog)
            self.check(dialog._preview is not None, dialog.feedback.text())
            result = dialog._preview
            self.check(
                result["status"] == "APPROXIMATE" and result["can_confirm"] is True,
                "Supported preview is not explicitly approximate",
            )
            self.check(
                result["certificate"]["math"]["counts"]["triangles"] == (96 if gothic else 64),
                "Independent D fixture triangle count changed",
            )
            self.check(self.w.project.to_dict() == source_state, "Preview replaced original target")
            self.capture("D-actual-approximate-preview", dialog)
            self.click(dialog.confirm)
            self.step(
                "D_actual_preview_whole_face_budget",
                elapsed_seconds=elapsed,
                budget_paper_mm=0.25,
                certificate=result["certificate"]["material_frame"],
                counts=result["certificate"]["math"]["counts"],
            )
            self.ok(dialog)

        self.modal(lambda: self.action("segment"), approximate)
        self.check(
            len(self.w.project.segmented_variants) == 1, "Confirmation did not create one variant"
        )
        vid = next(iter(self.w.project.segmented_variants))
        self.roles["D_variant"] = vid
        variant = self.w.project.segmented_variants[vid]
        self.check(
            variant.print_selected and self.w.project.loft_status(sid)["status"] == "REJECTED",
            "Confirming derived material falsely promoted original target",
        )
        self.check(
            all(
                self.w.project.placements[r["part_id"]].page_id is None
                for r in variant.triangle_bindings
            ),
            "Confirmation silently packed new parts",
        )
        self.add_page()
        half = 48 if gothic else 32
        self._manual_segment_half(vid, 0, 0, half)
        first_layout = copy.deepcopy(self.w.project.placements)
        self._manual_segment_half(vid, 1, half, half)
        full = copy.deepcopy(self.w.project.to_dict())
        self.shortcut(Qt.Key.Key_Z)
        self.check(
            self.w.project.placements == first_layout, "Undo did not restore whole manual batch"
        )
        self.shortcut(Qt.Key.Key_Y)
        self.check(self.w.project.to_dict() == full, "Redo did not restore exact batch/identities")
        if gothic:
            self.place(self.roles["D_front_wall"], 0, 35, 160)
            self.place(self.roles["D_back_wall"], 1, 35, 160)
        child = variant.triangle_bindings[0]["surface_id"]
        self.paper_drag(child, locked=False)
        self.place(child, 0, 25, 25, 17)
        self.click(self.w.position_lock)
        self.click(self.w.rotation_lock)
        self.paper_drag(child, locked=True)
        layout = copy.deepcopy(self.w.project.placements)
        # Source edit is a real property input; Ctrl+Z repairs it without losing
        # any material IDs, author placement, locks or the retained target.
        self.select(sid)
        self.data(self.w.vertex_choice, (second, vertex))
        self.number(self.w.vertex_y, 2400 if gothic else 1800)
        self.check(
            self.w.project.segmented_variant_status(vid)["status"] == "STALE",
            "Source change retained a false current approximation",
        )
        self.check(self.w.project.placements == layout, "Source edit moved author layout")
        self.check(
            any(i.severity == "error" for i in self.w.project.validate_layout()),
            "Stale confirmed variant did not block export",
        )
        self.capture("D-stale-source-error")
        self.shortcut(Qt.Key.Key_Z)
        self.check(
            self.w.project.segmented_variant_status(vid)["status"] == "APPROXIMATE"
            and self.w.project.placements == layout,
            "Undo failed to repair original source/layout",
        )
        self.select(child)
        self.linked_pick(only_surfaces=[r["surface_id"] for r in variant.triangle_bindings])
        self.capture("D-author-layout-before-save")
        self.finish("D-gothic" if gothic else "D-segmented")

    def audit_segmentation_vectors(self, directory, svgs, pdf):
        from vector_curve_oracle import pdf_stroked_areas, svg_signed_area

        target, vid = self.roles["D_target"], self.roles["D_variant"]
        project = self.w.project
        variant = project.segmented_variants[vid]
        self.check(
            project.loft_status(target)["status"] == "REJECTED", "Original target became EXACT"
        )
        by_part, expected_by_page = {}, {i: [] for i in range(len(project.pages))}
        for row, triangle in zip(
            variant.triangle_bindings, variant.certificate["math"]["triangles"]
        ):
            if "D_front_wall" not in self.roles:
                vertices = [
                    source_point(*map(float, map(Fraction, uv)))
                    for uv in triangle["parameter_vertices_exact"]
                ]
            else:
                surface = project.surfaces[target]
                reference = surface.params["correspondences"][triangle["patch_index"]]
                first, second = (project.profiles[pid] for pid in surface.source_profile_ids())
                vertices = []
                for uv in triangle["parameter_vertices_exact"]:
                    u, v = map(float, map(Fraction, uv))
                    ends = []
                    for side, profile in (("first", first), ("second", second)):
                        a, b = reference[side + "_interval"]
                        ends.append(
                            profile_point(profile, reference[side + "_segment_id"], a + (b - a) * u)
                        )
                    vertices.append([(1 - v) * a + v * b for a, b in zip(*ends)])
            expected = triangle_area(vertices)
            by_part[row["part_id"]] = expected
            place = project.placements[row["part_id"]]
            page_index = next(i for i, page in enumerate(project.pages) if page.id == place.page_id)
            expected_by_page[page_index].append(expected)
        wall_loops = {}
        for role in ("D_front_wall", "D_back_wall"):
            if role in self.roles:
                surface = project.surfaces[self.roles[role]]
                values = [
                    profile_area(project.profiles[pid]) for pid in surface.source_profile_ids()
                ]
                wall_loops[surface.part_id] = values
                by_part[surface.part_id] = values[0] - sum(values[1:])
                place = project.placements[surface.part_id]
                page_index = next(
                    i for i, page in enumerate(project.pages) if page.id == place.page_id
                )
                expected_by_page[page_index].extend(values)
        observations = []
        for svg in svgs:
            root = ET.parse(svg).getroot()
            for group in root:
                pid = group.get("data-part-id")
                if pid is None:
                    continue
                self.check(
                    pid in by_part, "SVG printed retained reference instead of actual material"
                )
                if pid not in wall_loops:
                    self.check(
                        group.get("data-flattening-mode") == "APPROXIMATE",
                        "SVG material lacks truthful source approximation metadata",
                    )
                cut = next(g for g in group if g.get("data-role") == "CUT")
                self.check(
                    len(cut) == (2 if pid in wall_loops else 1),
                    "Missing/duplicated actual CUT core or hole",
                )
                areas = [abs(svg_signed_area(path.get("d"))) for path in cut]
                net = max(areas) - (sum(areas) - max(areas))
                observations.append(
                    self.near(
                        net,
                        by_part[pid],
                        "D source triangle to actual SVG area",
                        0.01,
                    )
                )
        pdf_areas = pdf_stroked_areas(pdf)
        self.check(
            len(pdf_areas) == sum(map(len, expected_by_page.values())),
            "PDF omitted/duplicated a triangle core or true wall hole",
        )
        for page_index, wanted in expected_by_page.items():
            actual = sorted(value for index, value in pdf_areas if index == page_index)
            self.check(len(actual) == len(wanted), "PDF page material coverage mismatch")
            for a, b in zip(actual, sorted(wanted)):
                observations.append(self.near(a, b, "D source triangle to actual PDF area", 0.01))
        self.step(
            "D_actual_vector_coverage_source_triangle_areas",
            target_surface_id=target,
            variant_id=vid,
            material_count=len(by_part),
            reference_target_mode="REJECTED",
            output_mode="APPROXIMATE",
            observations=observations,
            scope="source triangle cores; no physical assembly or smooth EXACT claim",
        )
