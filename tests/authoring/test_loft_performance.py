"""Cache integrity regressions and a targeted offscreen probe of a real saved loft.

The CLI records latency, not novice usability or a native desktop proof.
"""

import copy
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from archpapercraft.authoring import AuthorProject, ValidationError, loft_surface


def small_loft():
    p = AuthorProject.new(scale=1)
    a = p.add_profile([[0, 0], [20, 0], [20, 10]], closed=False)
    b = p.copy_profile(a, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    sid = p.add_loft(
        a,
        b,
        correspondences=[
            {"first_segment_id": x.id, "second_segment_id": y.id}
            for x, y in zip(p.profiles[a].segments, p.profiles[b].segments)
        ],
    )
    return p, sid, a, b


def test_world_cache_returns_detached_payload_and_keys_actual_pose_not_revision(monkeypatch):
    p, sid, _, _ = small_loft()
    calls = []
    build = loft_surface._build_world_mesh

    def counted(*args):
        calls.append(1)
        return build(*args)

    monkeypatch.setattr(loft_surface, "_build_world_mesh", counted)
    loft_surface._world_mesh_json.cache_clear()
    first = p.world_geometry(sid)
    first["vertices"][0][0] = 999
    first["triangle_sources"][0]["uv"][0][0] = 999
    first["boundary"][0]["source"]["profile_id"] = "poison"
    next_mesh = p.world_geometry(sid)
    assert next_mesh["vertices"][0] == [0, 0, 0]
    assert next_mesh["triangle_sources"][0]["uv"][0][0] == 0
    assert next_mesh["boundary"][0]["source"]["profile_id"] != "poison"
    p.validate()
    p.set_placement(p.part_for_surface(sid), x_mm=10)
    assert len(calls) == 1  # Layout and validation reuse the SAME actual world source.
    revision = p.surfaces[sid].revision
    p.surfaces[sid].position_mm[:] = [5, 6, 7]  # Deliberately bypass command/revision.
    assert p.world_geometry(sid)["vertices"][0] == [5, 6, 7]
    assert len(calls) == 2 and p.surfaces[sid].revision == revision


@pytest.mark.parametrize("which", [0, 1])
def test_actual_profile_changes_invalidate_world_proof_without_revision_change(which):
    p, sid, a, b = small_loft()
    p.world_geometry(sid)
    profile = p.profiles[(a, b)[which]]
    revision = profile.revision
    profile.vertices[-1].point[:] = [0, 0]  # Invalid overlapping open source chain.
    assert profile.revision == revision
    with pytest.raises(ValidationError):
        p.validate()
    with pytest.raises(ValidationError):
        p.snapshot()


def test_canonical_material_cache_is_detached_and_actual_cache_poison_is_compared(monkeypatch):
    p, sid, _, _ = small_loft()
    pid = p.part_for_surface(sid)
    p.set_placement(pid, p.pages[0].id, 40, 40)
    calls = []
    build = loft_surface._build_loft_material_geometry

    def counted(*args):
        calls.append(1)
        return build(*args)

    monkeypatch.setattr(loft_surface, "_build_loft_material_geometry", counted)
    loft_surface._loft_material_json.cache_clear()
    detached = loft_surface.build_loft_part(p, p.parts[pid])
    detached.frame.anchor_vertex_id = "poison"
    detached.paths["CUT"][0]["commands"][0][1] = 999
    p.recompute()
    assert len(calls) == 1 and p.parts[pid].frame.anchor_vertex_id != "poison"
    assert p.parts[pid].paths["CUT"][0]["commands"][0][1] == 0
    # Equal-area translation of ONLY manufactured CUT must not reuse a
    # previously successful cache comparison or be accepted on area alone.
    for command in p.parts[pid].paths["CUT"][0]["commands"]:
        for index in range(1, len(command), 2):
            command[index] += 0.2
    p = AuthorProject.from_dict(p.to_dict())
    assert not p.parts[pid].stale  # A current capability is not a cache-repair bypass.
    assert "INVALID_CACHE" in [issue.code for issue in p.validate_layout()]
    with pytest.raises(ValidationError):
        p.snapshot()
    assert len(calls) == 1
    p.recompute()
    p.parts[pid].frame.anchor_vertex_id = p.profiles[p.surfaces[sid].profile_id].vertices[1].id
    p.recompute()
    assert len(calls) == 2
    assert p.parts[pid].polygons[sid][0][0] == [-20, 0]


def test_internal_validation_and_layout_do_not_copy_public_full_analysis(monkeypatch):
    p, sid, _, _ = small_loft()
    monkeypatch.setattr(
        loft_surface, "analysis", lambda *args: pytest.fail("Copied whole analysis")
    )
    p.validate()
    p.world_geometry(sid)
    p.loft_status(sid)
    p.validate_layout()


def test_exact_collinear_compaction_preserves_corners_rulings_and_curve_kinds():
    def line(a, b, source="a"):
        return {
            "kind": "line",
            "start": a,
            "end": b,
            "data": {},
            "source": {"profile_id": "profile", "segment_id": source},
        }

    chain = [
        line([0, 0], [1, 0]),
        line([1, 0], [2, 0]),
        line([2, 0], [4, 0]),
        {"kind": "line", "start": [4, 0], "end": [4, 10], "data": {}},
        line([4, 10], [2, 10], "b"),
        line([2, 10], [0, 10], "b"),
        {"kind": "line", "start": [0, 10], "end": [0, 0], "data": {}},
    ]
    before = copy.deepcopy(chain)
    assert loft_surface._commands(chain) == [
        ["M", 0, 0],
        ["L", 4, 0],
        ["L", 4, 10],
        ["L", 0, 10],
        ["Z"],
    ]
    assert chain == before
    assert loft_surface._commands([line([0, 0], [1, 0]), line([1, 0], [2, 0], "corner")])[1:3] == [
        ["L", 1, 0],
        ["L", 2, 0],
    ]
    assert len(loft_surface._commands([line([0, 0], [2, 0]), line([2, 0], [1, 0])])) == 4
    assert len(loft_surface._commands([line([0, 0], [1, 0]), line([1, 0], [2, 1e-16])])) == 4
    cubic = {
        "kind": "cubic",
        "start": [0, 0],
        "end": [3, 0],
        "data": {"control1": [1, 0], "control2": [2, 0]},
        "source": chain[0]["source"],
    }
    assert loft_surface._commands([cubic, line([3, 0], [4, 0])])[1][0] == "C"


def test_bezier_extrusion_cut_is_compact_but_source_parameter_map_remains_detailed():
    p = AuthorProject.new(scale=1)
    a = p.add_profile(
        segments=[
            {
                "kind": "cubic",
                "start": [0, 0],
                "end": [6, 0],
                "data": {"control1": [1, 0], "control2": [3, 0]},
            }
        ],
        closed=False,
    )
    b = p.copy_profile(a, plane={"origin": [0, 0, 10], "u": [1, 0, 0], "v": [0, 1, 0]})
    sid = p.add_loft(
        a,
        b,
        correspondences=[
            {
                "first_segment_id": p.profiles[a].segments[0].id,
                "second_segment_id": p.profiles[b].segments[0].id,
            }
        ],
    )
    assert p.profiles[a].segments[0].kind == "cubic"
    commands = p.parts[p.part_for_surface(sid)].paths["CUT"][0]["commands"]
    assert commands == [["M", 0.0, 0.0], ["L", 6.0, 0.0], ["L", 6.0, 10.0], ["L", 0.0, 10.0], ["Z"]]
    report = loft_surface.analysis(p, p.surfaces[sid])
    assert len(report["native"]["patches"][0]["first"]["segments"]) > 10
    assert report["area"]["status"] == "CERTIFIED"


def test_older_loft_cut_contract_loads_stale_without_rewriting_author_work(tmp_path, monkeypatch):
    from dataclasses import asdict

    from archpapercraft.authoring import load_project

    old_contract = "ANALYTIC_SIGNED_CREASES_AND_INTRINSIC_AREA_V1"
    current_contract = loft_surface.LOFT_PAPER_CONTRACT
    p, sid, _, _ = small_loft()
    pid = p.part_for_surface(sid)
    p.set_placement(
        pid, p.pages[0].id, 60, 60, 30, position_locked=True, rotation_locked=True
    )
    # Construct a preserved historical cache: same exact material locus but
    # redundant L commands and the pre-compaction capability digest.
    with monkeypatch.context() as legacy:
        legacy.setattr(loft_surface, "LOFT_PAPER_CONTRACT", old_contract)
        p.recompute()
    commands = p.parts[pid].paths["CUT"][0]["commands"]
    old_commands = [commands[0]]
    start = commands[0][1:]
    for command in commands[1:]:
        if command[0] == "L":
            end = command[1:]
            old_commands.append(["L", *[(a + b) / 2 for a, b in zip(start, end)]])
            start = end
        old_commands.append(command)
    p.parts[pid].paths["CUT"][0]["commands"] = old_commands
    historical = p.to_dict()
    original = copy.deepcopy(historical)
    source = tmp_path / "pre-compaction.apcraft"
    raw = json.dumps(historical, ensure_ascii=False).encode("utf-8")
    source.write_bytes(raw)

    loaded = load_project(source)
    assert loaded.parts[pid].stale
    status = loaded.loft_status(sid)
    assert status["status"] == "EXACT"  # Source remains exactly developable.
    assert status["paper_stale"] and status["paper_contract"] == current_contract
    assert [issue.code for issue in loaded.validate_layout()] == ["STALE"]
    with pytest.raises(ValidationError):
        loaded.snapshot()
    expected = copy.deepcopy(historical)
    expected["parts"][pid]["stale"] = True
    assert loaded.to_dict() == expected  # No implicit CUT/frame/ID/layout repair.
    assert historical == original and source.read_bytes() == raw

    loaded.recompute()
    assert loaded.loft_status(sid)["paper_contract"] == current_contract
    assert not loaded.loft_status(sid)["paper_stale"]
    assert not loaded.parts[pid].stale and not loaded.validate_layout()
    assert len(loaded.parts[pid].paths["CUT"][0]["commands"]) < len(old_commands)
    assert loaded.to_dict()["profiles"] == historical["profiles"]
    assert loaded.to_dict()["surfaces"] == historical["surfaces"]
    assert asdict(loaded.parts[pid].frame) == historical["parts"][pid]["frame"]
    assert loaded.to_dict()["placements"] == historical["placements"]
    assert loaded.parts.keys() == historical["parts"].keys()
    assert loaded.snapshot()["coverage"]["expected_part_ids"] == [pid]
    assert source.read_bytes() == raw
    loaded.save(tmp_path / "recomputed-copy.apcraft")
    restored = load_project(tmp_path / "recomputed-copy.apcraft")
    assert restored.to_dict() == loaded.to_dict()
    assert not restored.parts[pid].stale and not restored.loft_status(sid)["paper_stale"]


def latency_probe(source, output, *, label, qt=True):
    from archpapercraft.application.author_controller import AuthorController
    from archpapercraft.authoring import AuthorProject, loft_surface

    root = Path(__file__).resolve().parents[2]
    source = Path(source)
    raw = source.read_bytes()
    report = {
        "label": label,
        "evidence_scope": "BACKEND_AND_OFFSCREEN_QT_LATENCY_NOT_NATIVE_OR_NOVICE_PROOF",
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root)
        .decode()
        .strip(),
        "fixture": {"path": str(source), "sha256": hashlib.sha256(raw).hexdigest()},
        "runtime": {"loft_module": loft_surface.__file__, "qpa": os.environ.get("QT_QPA_PLATFORM")},
        "operations": {},
    }
    for name in ("loft_surface.py", "project.py", "paper.py"):
        file = root / "src/archpapercraft/authoring" / name
        report["runtime"][name] = hashlib.sha256(file.read_bytes()).hexdigest()

    def measured(name, operation):
        started = time.perf_counter()
        value = operation()
        report["operations"][name] = time.perf_counter() - started
        print(name, report["operations"][name], flush=True)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return value

    p = measured("cold_load_validate", lambda: AuthorProject.from_dict(json.loads(raw)))
    sid = next(sid for sid, surface in p.surfaces.items() if surface.kind == "ruled_loft")
    pid = p.part_for_surface(sid)
    measured("warm_world_mesh_1", lambda: p.world_geometry(sid))
    measured("warm_world_mesh_2", lambda: p.world_geometry(sid))
    status = measured("warm_status", lambda: p.loft_status(sid))
    report["loft_check"] = {
        "status": status["status"],
        "source_digest": status["source_digest"],
        "paper_stale": status["paper_stale"],
        "area_status": status["area"]["status"],
    }
    measured("warm_validate", p.validate)
    issues = measured("warm_layout", p.validate_layout)
    report["layout_issue_codes"] = [issue.code for issue in issues]
    controller = AuthorController()
    controller.project = p
    pos = p.placements[pid]
    measured(
        "placement_command",
        lambda: controller.execute(
            "Move real paper part", lambda project: project.set_placement(pid, x_mm=pos.x_mm + 1)
        ),
    )
    if qt:
        from PySide6.QtCore import QEventLoop, QSettings, QTimer
        from PySide6.QtWidgets import QApplication

        from archpapercraft.ui.author_window import AuthorMainWindow

        app = QApplication.instance() or QApplication([])
        window = AuthorMainWindow(
            settings=QSettings(str(Path(output).with_suffix(".ini")), QSettings.Format.IniFormat)
        )
        window.controller.project = p
        window.selected_surface = sid
        window.selected_profile = p.surfaces[sid].profile_id
        measured("qt_refresh", window.refresh)
        loop = QEventLoop()
        timer = QTimer()
        ticks = []
        timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
        timer.start(10)

        def command():
            measured(
                "qt_placement_command_and_refresh",
                lambda: window.controller.execute(
                    "Move real paper part",
                    lambda project: project.set_placement(pid, x_mm=pos.x_mm + 2),
                ),
            )
            QTimer.singleShot(100, loop.quit)

        QTimer.singleShot(50, command)
        loop.exec()
        timer.stop()
        report["qt_heartbeat_max_gap_seconds"] = max(
            (b - a for a, b in zip(ticks, ticks[1:])), default=0
        )
        window.controller._saved_digest = window.controller.digest(p.to_dict())
        window.close()
        app.processEvents()
    report["fixture_unchanged"] = (
        hashlib.sha256(source.read_bytes()).hexdigest() == report["fixture"]["sha256"]
    )
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--no-qt", action="store_true")
    args = parser.parse_args()
    latency_probe(args.source, args.output, label=args.label, qt=not args.no_qt)
