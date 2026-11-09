"""An uncertain layer must never downgrade an independent hard failure."""
# ruff: noqa: E402 -- Bind the reviewed worktree before importing application code.

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from archpapercraft.authoring import AuthorProject


def probe():
    project = AuthorProject.new(scale=1)

    def wall(x0, x1):
        profile = project.add_profile(
            [[x0, 0], [x1, 0], [x1, 20], [x0, 20]],
            plane={"origin": [0, 5, 0], "u": [1, 0, 0], "v": [0, 0, 1]},
        )
        return project.add_surface(profile), profile

    source, profile = wall(20, 60)
    base = project.add_surface(project.add_profile([[0, 0], [100, 0], [100, 100], [0, 100]]))
    relation = project.attach_edge_to_surface(
        source,
        project.profiles[profile].segments[0].id,
        base,
        target_side="outside",
        glue_direction=-1,
    )
    connector = project.set_attachment_tab(relation, width_mm=5, taper=1)
    # Independently exceeds the declared numeric support magnitude 1e6 paper mm.
    project.add_surface(
        project.add_profile(
            [[1e7, 0], [1e7 + 10, 0], [1e7 + 10, 10], [1e7, 10]],
        )
    )
    before = project.connector_bend_clearance(connector)
    source, profile = wall(70, 90)
    relation = project.attach_edge_to_surface(
        source,
        project.profiles[profile].segments[0].id,
        base,
        target_side="inside",
        glue_direction=-1,
    )
    project.set_attachment_tab(relation, width_mm=5, taper=1)
    after = project.connector_bend_clearance(connector)
    return dict(
        before=before,
        after=after,
        pass_=before["status"] == after["status"] == "UNRESOLVED",
        issue_codes=[issue.code for issue in project.validate_layout()],
    )


if __name__ == "__main__":
    result = probe()
    target = Path(sys.argv[1])
    target.write_text(json.dumps(result, indent=2), encoding="utf8")
    print("PASS" if result["pass_"] else "FAIL", "R01 preserved hard failure")
    raise SystemExit(0 if result["pass_"] else 1)
