"""Independent adapter/material checks; no production geometry helpers for expectations."""
# ruff: noqa: E402 -- Bind the reviewed worktree before importing application code.

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import AuthorProject, ProjectFormatError, ValidationError
from archpapercraft.exporter.author_export import SnapshotError, export_all


def authored():
    p = AuthorProject.new(scale=1)
    profile = p.add_profile(
        [[10, 0], [70, 0], [70, 30], [10, 30]],
        plane={"origin": [0, 7, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
    )
    wall = p.add_surface(profile)
    base = p.add_surface(p.add_profile([[0, 0], [120, 0], [120, 90], [0, 90]]))
    relation = p.attach_edge_to_surface(
        wall,
        p.profiles[profile].segments[0].id,
        base,
        target_side="outside",
        glue_direction=-1,
    )
    cid = p.set_attachment_tab(relation, width_mm=6, taper=1)
    return p, cid, wall, base


def snap(p):
    p.recompute()
    for index, pid in enumerate(p.parts):
        page = p.pages[0].id if index == 0 else p.add_page()
        p.set_placement(pid, page, 30, 40)
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    return p.snapshot()


def checks():
    results = []

    def record(name, condition, **detail):
        results.append(dict(name=name, pass_=bool(condition), **detail))
        assert condition, (name, detail)

    p, cid, wall, base = authored()
    profile = dict(thickness_mm=0.25, clearance_mm=0.02, bend_radius_mm=0.03, crease_zone_mm=0.6)
    p.set_material_profile(**profile)
    report = p.connector_bend_clearance(cid)
    record("known_complete_90_fold", report["status"] == "CLEAR", report=report)
    record(
        "finite_permissions_only_source_receiver",
        all(a["obstacle_id"] in (wall, base) for a in report["tabs"][0]["allowances"]),
    )
    record(
        "expected_geometry_in_world_paper_mm",
        {wall, base} <= set(report["tabs"][0]["checked_obstacle_ids"]),
    )
    first_key = report["assembly_digest"]
    pid = p.part_for_surface(wall)
    p.set_placement(pid, p.pages[0].id, 90, 80, 17)
    record("manual_layout_not_assembly_change", p._assembly_clearance_key() == first_key)
    p.add_profile([[1000, 0], [1001, 0], [1001, 1]])
    record("unused_draft_not_assembly_change", p._assembly_clearance_key() == first_key)
    p.set_material_profile(clearance_mm=0.04)
    record(
        "material_change_invalidates_cache",
        p._assembly_clearance_key() != first_key and p.parts[pid].stale,
    )

    before = p.to_dict()
    for invalid in (
        dict(thickness_mm=True),
        dict(crease_zone_mm=float("inf")),
        dict(bend_radius_mm=-0.1),
        dict(clearance_mm=float("nan")),
    ):
        try:
            p.set_material_profile(**invalid)
        except ValidationError:
            pass
        else:
            raise AssertionError(invalid)
    record("material_invalid_atomic", p.to_dict() == before)
    p.set_material_profile(**profile)
    obstruction = p.add_surface(
        p.add_profile(
            [[25, -3.5], [55, -3.5], [55, -2.5], [25, -2.5]],
            plane={"origin": [0, 4, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
        )
    )
    report = p.connector_bend_clearance(cid)
    record(
        "mid_fold_known_witness",
        report["status"] == "COLLISION" and report["tabs"][0]["obstacle_id"] == obstruction,
        report=report,
        independent_witness=[40, 4, -3],
        angle_deg=-45,
        endpoint_reason="initial y=7, final z=0; obstacle y=4 and -3.5<z<-2.5",
    )
    p.set_material_profile(thickness_mm=None)
    report = p.connector_bend_clearance(cid)
    record("mid_fold_unknown_witness_not_ignored", report["status"] == "COLLISION")

    temporary = Path(tempfile.mkdtemp(prefix="pc006b-material-independent-"))
    for schema, writer in ((1, "0.3.0-experimental"), (2, "0.3.0-pc006b-experimental")):
        old = AuthorProject.new()
        sid = old.add_surface(old.add_profile([[0, 0], [8000, 0], [0, 4000]]))
        data = old.to_dict()
        data.pop("material_profile")
        data.update(schema_version=schema, writer_version=writer)
        if schema == 1:
            data.pop("attachments")
            data.pop("next_attachment_number")
        path = temporary / f"old-{schema}.apcraft"
        path.write_text(json.dumps(data), encoding="utf8")
        original = path.read_bytes()
        controller = AuthorController()
        controller.open(path)
        record(
            f"schema{schema}_copy_required",
            controller.copy_source_path == path
            and controller.file_path is None
            and controller.project.parts[old.part_for_surface(sid)].stale,
        )
        controller.execute("material", lambda q: q.set_material_profile(thickness_mm=0.25))
        controller.undo()
        controller.redo()
        try:
            controller.execute("invalid", lambda q: q.set_material_profile(thickness_mm=-1))
        except ValidationError:
            pass
        try:
            controller.save(path)
        except ValueError:
            pass
        else:
            raise AssertionError("old source overwritten")
        controller.save(temporary / f"copy-{schema}.apcraft")
        record(
            f"schema{schema}_old_bytes_preserved_after_undo_failure_saveas",
            path.read_bytes() == original,
        )

    for mutation in (
        lambda d: d.pop("material_profile"),
        lambda d: d["material_profile"].update(grammage=200),
        lambda d: d.update(schema_version=4),
    ):
        data = AuthorProject.new().to_dict()
        mutation(data)
        try:
            AuthorProject.from_dict(data)
        except ProjectFormatError:
            pass
        else:
            raise AssertionError("corrupt/unknown schema accepted")
    record("strict_schema_no_implicit_material_default", True)

    p, cid, *_ = authored()
    snapshot = snap(p)
    directory = temporary / "export"
    export_all(snapshot, directory)
    original = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in directory.iterdir()}
    for bad_status in ("COLLISION", "UNRESOLVED"):
        bad = copy.deepcopy(snapshot)
        bad["construction_checks"]["connector_bends"][cid]["tabs"][0]["status"] = bad_status
        try:
            export_all(bad, directory)
        except SnapshotError:
            pass
        else:
            raise AssertionError("nested blocked motion exported")
        record(
            f"nested_{bad_status}_export_preserves_bundle",
            original
            == {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in directory.iterdir()},
        )
    # The obstacle below is actual authored tab material inside a receiver hole.
    # Its source and receiver material are independently outside the moving sweep.
    for known in (False, True):
        p, cid, *_ = authored()
        plane = {"origin": [0, 4, 0], "u": [1, 0, 0], "v": [0, 0, 1]}
        outer = p.add_profile([[0, -8], [100, -8], [100, 2], [0, 2]], plane=plane)
        hole = p.add_profile([[9, -6.2], [71, -6.2], [71, 0.3], [9, 0.3]], plane=plane)
        receiver = p.add_surface(outer)
        source_profile = p.add_profile(
            [[25, 0], [55, 0], [55, 4], [25, 4]],
            plane={"origin": [0, 0, -6.3], "u": [1, 0, 0], "v": [0, 1, 0]},
        )
        source = p.add_surface(source_profile)
        relation = p.attach_edge_to_surface(
            source,
            p.profiles[source_profile].segments[2].id,
            receiver,
            target_side="outside",
            glue_direction=-1,
        )
        other_cid = p.set_attachment_tab(relation, width_mm=6, taper=1)
        p.add_hole(receiver, hole)
        if known:
            p.set_material_profile(thickness_mm=0.25)
        report = p.connector_bend_clearance(cid)
        tab = report["tabs"][0]
        other_id = "tab:" + p.connectors[other_cid].tab_ids[0]
        record(
            f"other_tab_midmotion_{known}",
            report["status"] == "COLLISION" and tab["obstacle_id"] == other_id,
            report=report,
            independent_witness=[40, 4, -3],
            endpoint_clearance_reason="moving initial y=7, final z=0; static tab y=4, z=-6.3..-0.3",
        )
        record(
            f"other_tab_inventory_{known}",
            set(tab["expected_obstacle_ids"])
            == set(tab["checked_obstacle_ids"]) | set(tab["unresolved_layer_obstacle_ids"]),
        )
        issue = next(
            i
            for i in p.validate_layout()
            if i.code == "BEND_COLLISION" and i.joint_id == p.connectors[cid].attachment_id
        )
        record(
            f"other_tab_diagnostic_names_material_{known}",
            p.part_for_surface(source) in issue.part_ids
            and p.parts[p.part_for_surface(source)].name in issue.message
            and p.surfaces[source].name in issue.message
            and "tab:" not in issue.message,
            message=issue.message,
        )
        p.set_connector(other_cid, enabled=False)
        report = p.connector_bend_clearance(cid)
        record(
            f"other_tab_off_removes_only_material_{known}",
            report["status"] == ("CLEAR" if known else "UNVERIFIED"),
            report=report,
        )

    # Opposite sides have explicit uncertainty, not a fabricated zero-offset solid.
    for known in (False, True):
        p, cid, _, base = authored()
        sp = p.add_profile(
            [[80, 0], [100, 0], [100, 10], [80, 10]],
            plane={"origin": [0, 7, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
        )
        source = p.add_surface(sp)
        relation = p.attach_edge_to_surface(
            source,
            p.profiles[sp].segments[0].id,
            base,
            target_side="inside",
            glue_direction=-1,
        )
        other_cid = p.set_attachment_tab(relation, width_mm=6, taper=1)
        if known:
            p.set_material_profile(thickness_mm=0.25)
        report = p.connector_bend_clearance(cid)
        detail = report["tabs"][0]
        unresolved = "tab:" + p.connectors[other_cid].tab_ids[0]
        record(
            f"opposite_layer_uncertainty_{known}",
            report["status"] == ("UNRESOLVED" if known else "UNVERIFIED")
            and detail["unresolved_layer_obstacle_ids"] == [unresolved],
        )
        record(
            f"opposite_layer_complete_partition_{known}",
            set(detail["expected_obstacle_ids"])
            == set(detail["checked_obstacle_ids"]) | {unresolved}
            and unresolved not in detail["checked_obstacle_ids"],
        )
        obstacle = p.add_surface(
            p.add_profile(
                [[25, -3.5], [55, -3.5], [55, -2.5], [25, -2.5]],
                plane={"origin": [0, 4, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
            )
        )
        report = p.connector_bend_clearance(cid)
        record(
            f"opposite_uncertainty_cannot_erase_known_collision_{known}",
            report["status"] == "COLLISION" and report["tabs"][0]["obstacle_id"] == obstacle,
        )

    return dict(status="PASS", cases=results, temporary_directory=str(temporary))


if __name__ == "__main__":
    target = Path(__file__).with_name("pc006b-material-review-oracles.json")
    try:
        output = checks()
    except Exception as exc:
        output = dict(status="FAIL", error=repr(exc))
        target.write_text(json.dumps(output, indent=2), encoding="utf8")
        raise
    target.write_text(json.dumps(output, indent=2), encoding="utf8")
    print(output["status"], len(output["cases"]), "independent cases")
