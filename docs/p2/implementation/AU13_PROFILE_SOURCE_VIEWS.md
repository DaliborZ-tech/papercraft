# AU13: restricted analytic sources and semantic partitions

Runtime/API source: `a0073de13c6ceff182da605fa4cd6b2820df093e`, isolated
`revival/p2-profile-source-views`, based on published LINE `b2bbf89`.
Independent review is pending. This component is not complete AU13 application,
schema8 persistence, an actual UI/editor run, new-user testing or physical proof.

The self-contained descriptor has exactly these fields:
`schema=1, profile_id, history_id, piece_id, generation, source,
parameter_interval`. `source` is the canonical strict `CurveSource.to_dict()`;
parameters are canonical exact rational strings. It cannot name a callback or
factory. Qualified profile/piece IDs and the canonical floating cache are checked.
The application owner additionally binds it to the replayed active history piece.

`SourceCurveView.from_reference()` returns an immutable `Curve` subtype containing
the original source and exact oriented interval. `source_reference(history,id)`,
`canonical_projection(ref)` and `validate_projection(ref,kind,start,end,data)`
provide the schema8 application boundary. A source field of None retains the
existing `source_curve(profile,segment)` path. Polynomial controls stay rational;
the arc keeps original radius/center and phase, never deriving a new radius from
the rounded child start. `evaluate`, derivative, `_control`, bounded certification,
reverse and SVG source plans dispatch on that explicit source.

ARC span endpoints at source0/1 retain authored endpoints, including the allowed
legacy endpoint gap. Nominal analytic point bounds and the endpoint-gap bound are
separate. Exact cardinal turns are algebraic; other phases use the existing
outward trig intervals. A reverse swaps the original interval. `CurveSource.from_curve`
refuses a restricted view instead of silently turning its cache into a new source.

`semantic_reference_curves(profile,histories,references)` accepts a mapping of
root IDs to immutable History objects and ordered whole IDs or TrimReferences.
It returns status/curves/coverage/full_profile_coverage/why. Coverage attributes
every active child interval; source generation and current cache are checked.
Missing, overlapping, foreign-profile or mixed-generation answers remain
UNRESOLVED. Mathematical partial resolution is distinct from complete profile
coverage. It never repartitions the opposite loft profile or chooses a child.
`LoftProfile.from_profile(..., histories=..., references=...)` consumes that result.
Binary-identical full sources use the original legacy Curve and retain the same
loft patch count, phi mapping and numerical report after one-sided topology split.

`history_chord` exposes the whole semantic endpoint chord for a paper frame,
explicitly not a straight hinge. `historical_point` retains all owners of a
shared analytic point and resolves retired ARC/CUBIC split vertices after merge.
Application-level vertex UUID/alias and receiver-loop ownership remain root guards.

`native_projection_certificate` compares the original restricted source with its
actual decimal M/L/C/A controls: exact Bernstein differences for polynomials,
whole circle/phase bounds for arcs, and DIRECT signed Green area differences.
It is a numerical projection proof, not topology or contact permission.
`source_region_area_bounds` supplies one original NET body-minus-holes basis with
scale applied once, excluding tabs. It retains endpoint-gap metadata and does not
repair gaps or prove region containment.

Important consumer boundary: a partial ARC view cannot use the existing source
topology or loft kernels as if it were the neighboring endpoint-form A circle.
They return explicit UNRESOLVED. The native projected loop can separately be
VALID; the exact rational 60-degree cache point not satisfying x²+y²=400 proves
why those statements differ. The checked complete semantic source partition is
the integration path for topology-only ARC splits. CUBIC exact Bernstein paths
remain supported. The root application still wires schema8, source factories,
whole partitions, frames, real split/merge/scale/undo and persistent bend/UI users.

Verification: **362 selected tests PASS, 65.57 s** on the source pin, including
33 new source/geometry tests and existing LINE/projection/loft/area/topology/material
regressions. No full P2 or C runtime compatibility claim is made from this older
LINE-based worktree. Ruff and diff checks pass. The reviewer must assess the
math/API source and the later root integration separately.

[JUnit](evidence/au13-source-views-a0073de-targeted.xml) and
[backend numeric record](evidence/au13-source-views-a0073de.json) retain the
R20/arbitrary-third, exact cubic polynomial/area, source native area budgets,
semantic source coverage and legacy endpoint-gap cases.
