"""Opt-in PC009 edits after native reopen; all mutations use actual widgets."""

from __future__ import annotations

import copy
import math
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt

REOPEN_EDIT_FIXTURES = frozenset(
    {
        "model-A",
        "loft-Bezier",
        "loft-B1",
        "C-cylinder",
        "C-cone",
        "C-near",
        "D-segmented",
    }
)


class ReopenDesktopSteps:
    def edit_after_reopen(self, name):
        self.check(name in REOPEN_EDIT_FIXTURES, "No reviewed after-reopen edit for this fixture")
        before = copy.deepcopy(self.w.project.to_dict())
        placements = copy.deepcopy(self.w.project.placements)
        frames = {pid: copy.deepcopy(part.frame) for pid, part in self.w.project.parts.items()}
        depth = len(self.w.controller._undo)
        if name == "model-A":
            observation = self._reopen_roof_edit()
        elif name in ("loft-Bezier", "loft-B1"):
            observation = self._reopen_bezier_edit()
        elif name.startswith("C-"):
            observation = self._reopen_curved_tab_edit()
        else:
            observation = self._reopen_generation_edit()
        changed = copy.deepcopy(self.w.project.to_dict())
        commands = len(self.w.controller._undo) - depth
        self.check(
            changed != before and 0 < commands <= 2,
            "After-reopen widget edit did not create its bounded authored commands",
        )
        for _ in range(commands):
            self.shortcut(Qt.Key.Key_Z)
        self.check(
            self.w.project.to_dict() == before,
            "After-reopen Undo did not restore source, cache, layout and locks",
        )
        for _ in range(commands):
            self.shortcut(Qt.Key.Key_Y)
        self.check(
            self.w.project.to_dict() == changed,
            "After-reopen Redo lost exact new identities or authored values",
        )
        self.shortcut(Qt.Key.Key_R)
        if name == "D-segmented":
            self._layout_reopened_generation(observation)
        for pid, place in placements.items():
            self.check(
                self.w.project.placements[pid] == place,
                "After-reopen edit moved or unlocked existing manual work: " + pid,
            )
            self.check(
                self.w.project.parts[pid].frame == frames[pid],
                "After-reopen edit changed an existing paper anchor: " + pid,
            )
        if name == "model-A":
            self.near(
                self.net_area(self.roles["roof_north"]),
                108 * math.hypot(36, 36),
                "Reopened north roof area",
                0.01,
            )
        elif name in ("loft-Bezier", "loft-B1"):
            self.loft_depth_paper_mm = 11
        elif name.startswith("C-"):
            self.check(
                self.w.project.curved_connector_status(observation["connector_id"])["status"]
                == "CERTIFIED_APPROXIMATE",
                "Reopened curved tab edit did not retain a current bounded certificate",
            )
        self.reopened_edit_observation = observation
        self.capture(name + "-changed-after-reopen")
        self.step(
            "PC009_actual_widget_edit_after_reopen_undo_redo_preserves_manual_work",
            fixture=name,
            commands=commands,
            retained_placements=len(placements),
            observation=observation,
        )

    def _reopen_roof_edit(self):
        sid = self.roles["roof_north"]
        self.vertex(sid, 2, y=math.hypot(3600, 3600))
        self.vertex(sid, 3, y=math.hypot(3600, 3600))
        self.check(
            self.w.project.parts[self.w.project.part_for_surface(sid)].stale,
            "Second roof overhang edit did not stale the shared paper part",
        )
        return {
            "kind": "north_eave_500_to_600_model_mm",
            "surface_id": sid,
            "expected_shared_roof_area_mm2": 108 * (math.hypot(38, 38) + math.hypot(36, 36)),
        }

    def _reopen_bezier_edit(self):
        sid = self.roles["loft"]
        surface = self.w.project.surfaces[sid]
        second = surface.source_profile_ids()[1]
        self.select(sid)
        self.data(self.w.curve_choice, (second, self.w.project.profiles[second].segments[0].id))

        def edit(dialog):
            self.number(dialog.fields["depth"], 100 / self.w.unit_factor)
            self.ok(dialog)

        self.modal(lambda: self.action("profile_plane"), edit)
        self.check(
            self.w.project.parts[self.w.project.part_for_surface(sid)].stale,
            "Reopened profile-plane edit did not stale the dependent loft",
        )
        return {"kind": "loft_normal_depth_10_to_11_paper_mm", "profile_id": second}

    def _reopen_curved_tab_edit(self):
        cid = self.circular_observation["connector_id"]
        record = self.w.project.curved_connectors[cid]
        slot = record.slot_ids[1]
        self.select(record.owner_surface_id)
        self.data(self.w.curved_panel.sets, cid)
        self.data(self.w.curved_panel.tabs, slot)

        def edit(dialog):
            self.check(dialog.source_slot_ids[1] == slot,
                       "Reopened dialog slot index belongs to another source identity")
            self.combo(dialog.tabs, 1)  # Dialog choices use stable slot indices; panel uses UUIDs.
            self.number(dialog.tip, 0.02)
            packet = self._c_preview(dialog)
            self.check(packet["status"] == "CERTIFIED_APPROXIMATE", dialog.feedback.text())
            self.click(dialog.apply_button)

        self.modal(lambda: self.click(self.w.curved_panel.edit), edit)
        self.check(
            self.w.project.curved_connectors[cid].tab_overrides[slot]["tip_offset_mm"] == 0.02,
            "Reopened authored tip offset was not stored in the same slot",
        )
        return {
            "kind": "curved_tip_offset_001_to_002_paper_mm",
            "connector_id": cid,
            "slot_id": slot,
        }

    def _reopen_generation_edit(self):
        target = self.roles["D_target"]
        previous = self.roles["D_variant"]
        variants = set(self.w.project.segmented_variants)
        self.select(target)
        self.data(self.w.generation_choice, None)

        def edit(dialog):
            self.number(dialog.deviation, 0.125)
            self._wait_segment_preview(dialog)
            result = dialog._preview
            self.check(
                result is not None and result["can_confirm"] and result["status"] == "APPROXIMATE",
                dialog.feedback.text(),
            )
            self.click(dialog.confirm)
            self.ok(dialog)

        self.modal(lambda: self.action("segment"), edit)
        created = set(self.w.project.segmented_variants) - variants
        self.check(len(created) == 1, "Reopened refinement did not retain old and new generations")
        vid = created.pop()
        self.check(
            not self.w.project.segmented_variants[previous].print_selected
            and self.w.project.segmented_variants[vid].print_selected,
            "New approved generation did not become the explicit print material",
        )
        self.check(
            self.w.project.loft_status(target)["status"] == "REJECTED",
            "Refinement falsely promoted the original smooth target to EXACT",
        )
        return {
            "kind": "additional_approved_generation_0125_paper_mm",
            "previous_generation_id": previous,
            "new_generation_id": vid,
        }

    def _layout_reopened_generation(self, observation):
        vid = observation["new_generation_id"]
        rows = self.w.project.segmented_variants[vid].triangle_bindings
        self.check(2 <= len(rows) <= 160, "Refined material exceeds this explicit two-page grid")
        self.check(
            all(self.w.project.placements[row["part_id"]].page_id is None for row in rows),
            "New generation was silently packed before author layout",
        )
        half = (len(rows) + 1) // 2
        self._manual_segment_half(vid, 0, 0, half)
        self._manual_segment_half(vid, 1, half, len(rows) - half)
        self.place(rows[0]["surface_id"], 0, 25, 25, 17)
        self.click(self.w.position_lock)
        self.click(self.w.rotation_lock)
        self.roles["D_variant"] = vid
        observation["new_printed_part_count"] = len(rows)

    def audit_after_reopen_vectors(self, name, svgs, pdf):
        if name != "model-A":
            return  # Existing B/C/D independent readers already consume their changed source.
        from vector_curve_oracle import pdf_stroked_areas, svg_signed_area

        observation = self.reopened_edit_observation
        expected = observation["expected_shared_roof_area_mm2"]
        pid = self.w.project.part_for_surface(observation["surface_id"])
        groups = [
            g for svg in svgs for g in ET.parse(svg).getroot() if g.get("data-part-id") == pid
        ]
        self.check(len(groups) == 1, "Changed shared roof missing or duplicated in SVG")
        cuts = next(role for role in groups[0] if role.get("data-role") == "CUT")
        self.near(
            sum(abs(svg_signed_area(path.get("d"))) for path in cuts),
            expected,
            "Actual reopened shared-roof SVG area",
            0.01,
        )
        matches = [
            value
            for page, value in pdf_stroked_areas(pdf)
            if page == 1 and abs(value - expected) <= 0.01
        ]
        self.check(len(matches) == 1, "Actual PDF does not contain the changed shared-roof area")
        self.step(
            "PC009_reopened_north_roof_change_in_actual_vectors",
            expected_shared_roof_area_mm2=expected,
            pdf_area_mm2=matches[0],
        )
