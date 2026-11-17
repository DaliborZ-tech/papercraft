"""Detached publishers must require the same history authority as project loading."""

import copy
import json
from fractions import Fraction

import pytest

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring.loft_surface import _bound_analysis, _source_context
from archpapercraft.authoring.project import ProjectFormatError
from archpapercraft.exporter.author_export import export_all
from archpapercraft.exporter.curve_output_validation import CurveOutputError
from archpapercraft.exporter.loft_output_validation import _digest, validate_loft_snapshot


def merged_loft(kind):
    p = AuthorProject.new(scale=0.1)
    profiles = []
    for height in (0, 10):
        segment = (
            dict(kind="arc", start=[20, 0], end=[-20, 0], data=dict(center=[0, 0], sweep_deg=180))
            if kind == "arc"
            else dict(
                kind="cubic", start=[0, 0], end=[4, 0], data=dict(control1=[0, 4], control2=[4, 4])
            )
        )
        pid = p.add_profile(
            segments=[segment],
            closed=False,
            plane=dict(origin=[0, 0, height], u=[1, 0, 0], v=[0, 1, 0]),
        )
        split = p.split_profile_segment(pid, p.profiles[pid].segments[0].id, Fraction(1, 3))
        p.merge_profile_segments(pid, split["segment_ids"])
        profiles.append(pid)
    a, b = profiles
    sid = p.add_loft(
        a,
        b,
        correspondences=[
            dict(
                first_segment_id=p.profiles[a].segments[0].id,
                second_segment_id=p.profiles[b].segments[0].id,
            )
        ],
    )
    p.set_placement(p.part_for_surface(sid), p.pages[0].id, 40, 50)
    for issue in p.validate_layout():
        if issue.severity == "warning":
            p.acknowledge(issue.id)
    return p, sid


@pytest.mark.parametrize("operation", ["validate", "writer"])
def test_detached_merged_descriptor_requires_history(operation, tmp_path):
    p, sid = merged_loft("cubic")
    snapshot = p.snapshot()
    validate_loft_snapshot(snapshot)
    report = snapshot["construction_checks"]["lofts"][sid]
    binding = report["source_binding"]
    binding["profile_subdivisions"] = {}
    # Digest agreement is not independent authority: an untrusted snapshot can
    # recompute its declared hashes after deleting the mandatory replay record.
    intrinsic = dict(
        profiles=binding["profiles"], params=binding["surface"]["params"], scale=binding["scale"]
    )
    report["intrinsic_source_digest"] = _digest(intrinsic)
    report["source_digest"] = _digest(
        dict(intrinsic_source_digest=report["intrinsic_source_digest"], surface=binding["surface"])
    )
    # Rebuild the internally consistent representation too. Merely retaining
    # the old certificate fails safely for an incidental digest mismatch.
    analysis = _bound_analysis(
        json.dumps(intrinsic, sort_keys=True), json.dumps(binding["surface"], sort_keys=True)
    )
    assert analysis["status"] == "EXACT"
    report["representation"] = analysis["representation"]
    with pytest.raises((CurveOutputError, ValueError)):
        if operation == "validate":
            validate_loft_snapshot(snapshot)
        else:
            export_all(snapshot, tmp_path / "rejected")
    assert not (tmp_path / "rejected" / "model.pdf").exists()


@pytest.mark.parametrize("kind", ["arc", "cubic"])
def test_detached_source_context_requires_history_even_if_registry_empty(kind):
    p, sid = merged_loft(kind)
    binding = p.loft_status(sid)["source_binding"]
    intrinsic = dict(
        profiles=binding["profiles"], params=binding["surface"]["params"], scale=binding["scale"]
    )
    with pytest.raises(ValueError):
        _source_context(json.dumps(intrinsic), json.dumps(binding["surface"]))


@pytest.mark.parametrize("retired", ["root", "left", "right"])
def test_retired_line_identity_rejected_after_inverse_merge(retired):
    p = AuthorProject.new(scale=1)
    pid = p.add_profile([[0, 0], [12, 0]], closed=False)
    root = p.profiles[pid].segments[0].id
    split = p.split_profile_segment(pid, root, Fraction(1, 3))
    p.merge_profile_segments(pid, split["segment_ids"])
    state = copy.deepcopy(p.to_dict())
    state["profiles"][pid]["segments"][0]["id"] = dict(
        root=root, left=split["segment_ids"][0], right=split["segment_ids"][1]
    )[retired]
    state["profiles"][pid]["segments"][0]["source_reference"] = None
    with pytest.raises(ProjectFormatError):
        AuthorProject.from_dict(json.loads(json.dumps(state)))
