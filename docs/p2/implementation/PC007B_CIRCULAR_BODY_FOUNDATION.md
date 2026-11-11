# PC-007B: analytic circular body foundation

Component scope only; independent review, C connector composition, actual UI,
new-user usability and physical assembly remain pending.

The existing manual `add_profile` → `add_loft` path recognizes complete coaxial
circles with an exact common rational orthonormal basis. Source arcs must be
quarter/half turns with exact rotated endpoints and matching oriented coverage.
Other sources use the unchanged general loft pipeline. No preset, bottom disk,
new surface kind or persistence schema is introduced.

The cylinder produces native L; a frustum produces native circular A, split
into strictly minor intervals. The full supplied A/L topology and area are
checked. Intrinsic source area is independently enclosed from actual binary
radii/height/scale using `pi*(R0+R1)*sqrt((R1-R0)^2+H^2)`. Native endpoint-circle
center/angle and total boundary-length intervals are checked separately from
display chords. Material envelopes include that separate display uncertainty.
Near unequal radii stay a cone; insufficient finite precision falls back
truthfully, never through an epsilon cylinder classification.

`project.circular_rim(surface_id, side, source_turn=0)` returns detached source
IDs/intervals/seams, native radius and slope as exact rational strings, actual
source parameter intervals, world-frame enclosures, the reflected-or-proper
reference chart→paper affine map, actual native A/L boundary, and source digest.
`_circular_rim_binding(..., part_override=bare_part)` is the source-only callback
entry: no material-cache approval, no `part_input` or recursive body rebuild.
Native reference radii are coupled to a common sector angle; the second radius
is not rounded independently. Source and native slope/radius are distinguished.

The output guard binds canonical A/L to both live source profiles/frame. Actual
SVG arcs are checked through interval centers/angles/lengths; actual PDF cubic
chains are checked against interval circle Hermite controls plus whole-interval
fourth-derivative remainder and independently bounded actual cubic lengths.
Original source→actual position, length and area tolerances remain unchanged.
V5 is the paper-cache capability, not a new document schema: old V4 caches load
stale, remain untouched until explicit recompute, and preserve frame/layout/IDs.
Current-capability equal-area cache poison remains blocked.

Verification: the earlier integration selection passed 154 tests; after the
final rim API additions, 35 targeted tests and 16 core tests passed (overlapping
selections, not an added total). Tests include actual SVG/PDF publication for
R10/H30 cylinder, R10→20/slant≈30 frustum, and R10→10.000001/H30 near-cylinder;
900π/600π area expectations, source direction/negative axis, cache recovery,
current-cache poison, reflected A transforms and read-only source-frame binding.
JUnit files: `Cbody-targeted-run02.xml`, `Cbody-final-API-run03.xml` in local Temp.

**Not yet certified:** source/native uncertainty transfer for the full curved
tab collar Jacobian/strain. Tangential derivative bounds and frame intervals
are inputs, not that proof. Source-transfer, shared-base trimming/body+tab union,
registry hooks and BODY_ONLY area-budget integration are separate follow-ups.
No actual editor, desktop, new-user or physical C proof is claimed here.
