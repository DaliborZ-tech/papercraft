"""Independently replay actual saved run05 A without changing its original file."""
# ruff: noqa: E402 -- Bind reviewed worktree before application imports.

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from archpapercraft.application.author_controller import AuthorController

source = (
    ROOT / "docs/p2/implementation/evidence/pc006b-desktop-d2a3b73-run05/model-A/model-A.apcraft"
)
original_bytes = source.read_bytes()
controller = AuthorController()
controller.open(source)
before = copy.deepcopy(controller.project.to_dict())
revisions = {pid: p.source_revision for pid, p in controller.project.parts.items()}
controller.recompute()
cases = [
    dict(
        name="actual_native_A_redundant_recompute_exact_noop",
        pass_=controller.project.to_dict() == before
        and not controller.dirty
        and not controller.can_undo,
        revisions=revisions,
    )
]
controller.execute("Material change", lambda p: p.set_material_profile(crease_zone_mm=0.55))
assert all(p.stale for p in controller.project.parts.values())
controller.recompute()
cases.append(
    dict(
        name="actual_native_A_material_change_advances_source_evidence",
        pass_=all(
            p.source_revision == controller.project.revision > revisions[pid]
            for pid, p in controller.project.parts.items()
        ),
    )
)
after = copy.deepcopy(controller.project.to_dict())
controller.recompute()
cases.append(
    dict(
        name="recompute_after_changed_source_is_stable_again",
        pass_=controller.project.to_dict() == after,
    )
)

small = AuthorController()
small.new(scale=1)
sid = small.execute(
    "Own material", lambda p: p.add_surface(p.add_profile([[0, 0], [30, 0], [30, 20], [0, 20]]))
)
pid = small.project.part_for_surface(sid)
old = small.project.parts[pid].source_revision
profile = small.project.profiles[small.project.surfaces[sid].profile_id]
vid = profile.vertices[1].id
small.execute("Own contour change", lambda p: p.move_vertex(profile.id, vid, [35, 0]))
small.recompute()
cases.append(
    dict(
        name="real_contour_edit_advances_source_evidence",
        pass_=small.project.parts[pid].source_revision == small.project.revision > old,
    )
)
cases.append(
    dict(
        name="original_native_project_bytes_preserved", pass_=source.read_bytes() == original_bytes
    )
)
output = dict(status="PASS" if all(c["pass_"] for c in cases) else "FAIL", cases=cases)
Path(__file__).with_suffix(".json").write_text(json.dumps(output, indent=2), encoding="utf8")
print(output["status"], len(cases), "independent recompute cases")
raise SystemExit(0 if output["status"] == "PASS" else 1)
