"""Bounded, attached curved-rim tabs with an explicit deforming relief collar.

This is a DIGITAL APPROXIMATION, not an elastic-paper or physical-fit proof.
The body is the open analytic cylinder/cone below its rim plane. The receiver
is a disk minus circular holes. External obstacles are outside this API scope.
All positive decisions use rational inequalities over the entire material and
fold interval; floating evaluation is provided ONLY for previews/oracle checks.
See PC007B_CURVED_TABS_PROOF.md for the map and the analytic bounds.
"""

import math
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from uuid import NAMESPACE_URL, uuid5


def _q(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a geometric quantity")
    if isinstance(value, str) and len(value) > 4096:
        raise ValueError("Geometric arithmetic input budget exceeded")
    try:
        result = Fraction(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Geometry requires finite numeric quantities") from exc
    if max(result.numerator.bit_length(), result.denominator.bit_length()) > 16384:
        raise ValueError("Geometric arithmetic input budget exceeded")
    return result


def _sqrt(value):
    scale = 10**40
    root = math.isqrt(value.numerator*scale*scale // value.denominator)
    low = Fraction(root, scale)
    return low, low if low*low == value else Fraction(root+1, scale)


def _round(interval):
    scale = 10**40
    a, b = interval
    return (Fraction(a.numerator*scale//a.denominator, scale),
            Fraction(-((-b.numerator*scale)//b.denominator), scale))


def _add(a, b):
    return _round((a[0]+b[0], a[1]+b[1]))


def _mul(a, b):
    products = [x*y for x in a for y in b]
    return _round((min(products), max(products)))


def _atan(value):
    if not 0 <= value <= Fraction(1, 4):
        raise ValueError("Small circular arc required")
    result, power = Fraction(0), value
    for index in range(96):
        result += (-1)**index*power/(2*index+1)
        power *= value*value
        error = power/(2*index+3)
        if error < Fraction(1, 10**65):
            return (result-error if index % 2 == 0 else result,
                    result if index % 2 == 0 else result+error)
    raise ValueError("Arc interval budget exhausted")


@lru_cache(maxsize=1)
def _pi():
    a, b = _atan(Fraction(1, 5)), _atan(Fraction(1, 239))
    return 16*a[0]-4*b[1], 16*a[1]-4*b[0]


@lru_cache(maxsize=512)
def _rotation(turn):
    """Outward sin/cos of an exact turn; Taylor plus Lipschitz angle error."""
    turn = turn % 1
    if turn > Fraction(1, 2):
        turn -= 1
    angle = tuple(2*p*turn for p in _pi())
    middle, error = sum(angle)/2, abs(angle[1]-angle[0])/2
    output = []
    for cosine in (False, True):
        power = (Fraction(1), Fraction(1)) if cosine else (middle, middle)
        result = (Fraction(0), Fraction(0))
        for i in range(64):
            signed = power if i % 2 == 0 else (-power[1], -power[0])
            result = _add(result, signed)
            n = 2*i if cosine else 2*i+1
            power = _mul(power, (middle*middle/((n+1)*(n+2)),)*2)
        # For |angle|<=π, the alternating tail after64 terms is bounded by
        # the next term. Interval arithmetic encloses all rounded operations.
        tail = max(abs(value) for value in power)
        output.append((result[0]-tail-error, result[1]+tail+error))
    return output[0], output[1]


@dataclass(frozen=True)
class Rim:
    radius_mm: object
    radial_slope: object
    rim_id: str
    body_id: str
    seam_turn: object = 0


@dataclass(frozen=True)
class Tab:
    tab_id: str
    center_turn: object
    nominal_base_mm: object
    depth_mm: object
    relief_mm: object
    owner_id: str
    receiver_id: str
    enabled: bool = True
    tip_offset_mm: object = 0
    contact_side: str = "back"
    requested_min_gap_mm: object = 0


@dataclass(frozen=True)
class CircularHole:
    x_mm: object
    y_mm: object
    radius_mm: object


@dataclass(frozen=True)
class Cap:
    radius_mm: object
    part_id: str
    holes: tuple = ()
    contact_side: str = "front"
    plane_offset_mm: object = 0


@dataclass(frozen=True)
class Limits:
    max_position_mm: object
    max_differential_deformation: object
    min_glue_area_mm2: object
    thickness_mm: object
    clearance_mm: object
    bend_radius_mm: object = 0
    area_uncertainty_mm2: object = Fraction(1, 100000)


def periodic_tabs(rim, receiver_id, *, count, depth_mm, relief_mm,
                  nominal_base_mm=None, gap_mm=None):
    """Stable slot identity survives off/custom edits and changing dimensions."""
    if type(count) is not int or not 1 <= count <= 1000:
        raise ValueError("Tab count must be an integer between1 and1000")
    if (nominal_base_mm is None) == (gap_mm is None):
        raise ValueError("Specify either nominal base or a requested minimum source gap")
    if gap_mm is not None:
        gap_mm = _q(gap_mm)
        if gap_mm < 0:
            raise ValueError("Requested source gap cannot be negative")
        width = 2*_pi()[0]*_q(rim.radius_mm)/count-gap_mm
        scale = 10**24
        nominal_base_mm = Fraction(width.numerator*scale//width.denominator, scale)
        if nominal_base_mm <= 0:
            raise ValueError("Requested gaps leave no positive source interval")
    return tuple(Tab(str(uuid5(NAMESPACE_URL, f"papercraft:{rim.rim_id}:slot:{i}")),
                     (_q(rim.seam_turn)+Fraction(2*i+1, 2*count)) % 1,
                     nominal_base_mm, depth_mm, relief_mm,
                     rim.body_id, receiver_id, requested_min_gap_mm=gap_mm or 0)
                 for i in range(count))


def _geometry(rim, tab):
    r, k = _q(rim.radius_mm), _q(rim.radial_slope)
    b, depth, relief, offset = map(_q, (tab.nominal_base_mm, tab.depth_mm,
                                      tab.relief_mm, tab.tip_offset_mm))
    if r <= 0 or abs(k) >= 1 or b <= 0 or not 0 < relief < depth < r:
        raise ValueError("Positive radius/base and0<relief<depth<radius; |slope|<1 required")
    parameter = k*b/(4*r)
    if abs(parameter) > Fraction(1, 16):
        raise ValueError("Native source arc exceeds the supported short-arc domain")
    xe = b/2/(1+parameter*parameter)
    fe = -k*b*b/(8*r)/(1+parameter*parameter)
    if abs(offset) > xe/2:
        raise ValueError("Custom triangle apex must remain within half the base halfwidth")
    if k:
        angles = _atan(abs(parameter))
        angles = (2*angles[0]/abs(k), 2*angles[1]/abs(k))
    else:
        angles = (b/(2*r),)*2
    a = angles[1]
    if a > Fraction(1, 4):
        raise ValueError("Source rim interval exceeds a quarter radian halfspan")
    cosine = 1-(k*a)**2/2
    f_bound = r*abs(k)*a*a/2
    fprime = abs(k)*a/cosine
    collar_height = relief-f_bound
    if collar_height <= 0 or (depth-fe)/(xe+abs(offset)) <= fprime:
        raise ValueError("Flat triangle sides or relief do not clear the native curved base")
    d0 = r*a*a/2+r*(1+k*k)*a**3/6
    position = d0+f_bound
    ex = a/cosine+(1/cosine-1)+fprime+fprime*position/collar_height
    ey = position/collar_height
    perturbation = _sqrt(ex*ex+ey*ey)[1]
    # Bound singular-value strain from JᵀJ, not ||J-Q|| alone: a varying
    # rotation of the collar basis must not be mislabeled as material stretch.
    tangent_defect = r*(1+k*k)*a**3/6
    radial_defect = r*a*a/2+f_bound
    xx = 2*((1+k*k)*a*a/(2*cosine)+fprime*tangent_defect/collar_height)+ex*ex
    yy = 2*radial_defect/collar_height+ey*ey
    xy = (tangent_defect/collar_height+a/cosine+fprime
          +fprime*radial_defect/collar_height+ex*ey)
    metric_error = max(xx+xy, yy+xy)
    deformation = (min(perturbation, 1-_sqrt(1-metric_error)[0])
                   if metric_error < 1 else perturbation)
    h = _sqrt(1-k*k)[0]
    body_lower = relief*h-d0-depth*a
    # At final fold the collar is injective: its tangential coordinate is
    # strictly increasing in x; its radial coordinate is strictly decreasing
    # along a fixed tangent coordinate. Above the collar the map is rigid.
    injective_margin = ((1-(1+k*k)*a*a/(2*cosine))*(1-r*a*a/(2*relief))
                        -a/cosine*tangent_defect/relief)
    ratio = (depth-relief)/(depth-fe)
    left = -xe*ratio+offset*(1-ratio)
    right = xe*ratio+offset*(1-ratio)
    glue = ((r-relief, left), (r-relief, right), (r-depth, offset))
    flat = [("M", -xe, fe)]
    hinge = (("L", xe, fe),) if not k else (
        ("A", abs(r/k), abs(r/k), 0, 0, int(k < 0), xe, fe),)
    flat.extend(hinge)
    flat.extend((("L", offset, depth), ("Z",)))
    return {"radius": r, "slope": k, "half_angle": _round(angles), "xe": xe, "fe": fe,
            "depth": depth, "relief": relief, "offset": offset,
            "flat_native_loop": tuple(flat), "shared_base_commands": (flat[0], *hinge),
            "cut_side_commands": (("M", xe, fe), ("L", offset, depth), ("L", -xe, fe)),
            "glue_triangle_local": glue, "position_bound_mm": _round((position,)*2)[1],
            "differential_deformation_bound": _round((deformation,)*2)[1],
            "jacobian_perturbation_bound": _round((perturbation,)*2)[1],
            "metric_operator_error_bound": _round((metric_error,)*2)[1],
            "collar_injectivity_margin": _round((injective_margin,)*2)[0],
            "body_distance_lower_mm": _round((body_lower,)*2)[0],
            "source_arc_length_bounds_mm": _round(tuple(2*r*v for v in angles)),
            "angular_sector_half_bound": _round((max(xe/(r-abs(fe)),
                                                       abs(offset)/(r-depth)),)*2)[1]}


def _global_triangle(triangle, turn):
    sine, cosine = _rotation(turn)
    result = []
    for radial, tangent in triangle:
        result.append((_add(_mul((radial,)*2, cosine),
                            _mul((-tangent,)*2, sine)),
                       _add(_mul((radial,)*2, sine), _mul((tangent,)*2, cosine))))
    return tuple(result)


def _area(triangle):
    a, b, c = triangle
    return abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2


def _distance_box_squared(box, center):
    low, high = Fraction(0), Fraction(0)
    for interval, value in zip(box, center):
        differences = (interval[0]-value, interval[1]-value)
        low += 0 if differences[0] <= 0 <= differences[1] else min(x*x for x in differences)
        high += max(x*x for x in differences)
    return low, high


def _contact(triangle, turn, cap, budget, max_depth, area_error):
    outer = _q(cap.radius_mm)
    holes = tuple((_q(h.x_mm), _q(h.y_mm), _q(h.radius_mm)) for h in cap.holes)
    if outer <= 0 or any(h[2] <= 0 for h in holes):
        raise ValueError("Receiver disk and hole radii must be positive")
    queue = [(triangle, 0)]
    low = unknown = outside = Fraction(0)
    while queue:
        cell, depth = queue.pop()
        area = _area(cell)
        if budget[0] <= 0:
            unknown += area+sum((_area(t) for t, _ in queue), Fraction(0))
            break
        budget[0] -= 1
        vertices = _global_triangle(cell, turn)
        box = tuple((min(p[i][0] for p in vertices), max(p[i][1] for p in vertices))
                    for i in range(2))
        covered = all(x*x+y*y <= outer*outer for x, y in cell)
        excluded = _distance_box_squared(box, (0, 0))[0] > outer*outer
        for x, y, radius in holes:
            distances = [_distance_box_squared(p, (x, y)) for p in vertices]
            if all(d[1] < radius*radius for d in distances):
                excluded = True
            if _distance_box_squared(box, (x, y))[0] <= radius*radius:
                covered = False
        if excluded:
            outside += area
        elif covered:
            low += area
        elif depth >= max_depth or area <= area_error:
            unknown += area
        else:
            a, b, c = cell
            ab, bc, ca = (tuple((x+y)/2 for x, y in zip(p, q))
                          for p, q in ((a, b), (b, c), (c, a)))
            queue.extend((t, depth+1) for t in ((a, ab, ca), (ab, b, bc),
                                               (ca, bc, c), (ab, bc, ca)))
    return low, low+unknown, outside


def _certain_overlap(first, second):
    # A strictly common interior point proves positive-area overlap. Failure is
    # not absence: complete-sector distance must independently prove CLEAR.
    for source, target in ((first, second), (second, first)):
        point = tuple((sum(v[i][0] for v in source)/3,
                       sum(v[i][1] for v in source)/3) for i in range(2))
        signs = []
        for a, b in zip(target, (*target[1:], target[0])):
            dx = (b[0][0]-a[0][1], b[0][1]-a[0][0])
            dy = (b[1][0]-a[1][1], b[1][1]-a[1][0])
            px = (point[0][0]-a[0][1], point[0][1]-a[0][0])
            py = (point[1][0]-a[1][1], point[1][1]-a[1][0])
            p, q = _mul(dx, py), _mul(dy, px)
            signs.append((p[0]-q[1], p[1]-q[0]))
        if all(s[0] > 0 for s in signs) or all(s[1] < 0 for s in signs):
            return True
    return False


def certify_tabs(rim, tabs, cap, limits, *, max_cells=10000, max_depth=14, max_pairs=10000,
                 unresolved_obstacle_ids=()):
    """Certify the stated APPROXIMATE map, never physical elasticity or full P2.

    All limits are explicit; no minimum glue default is silently lowered.
    Known negatives dominate unrelated unknown material/budget. Positive status
    requires every active tab and every unordered pair to have complete proofs.
    A body adapter must use the supplied native shared base unchanged, transform
    the true source interval, and independently validate actual published output.
    """
    if type(max_cells) is not int or max_cells < 0:
        raise ValueError("Cell budget must be a nonnegative integer")
    if type(max_depth) is not int or not 0 <= max_depth <= 24:
        raise ValueError("Depth budget must be between0 and24")
    if type(max_pairs) is not int or max_pairs < 0:
        raise ValueError("Pair budget must be a nonnegative integer")
    tabs = tuple(tabs)
    if len(tabs) > 1000 or len({tab.tab_id for tab in tabs}) != len(tabs):
        raise ValueError("Unique stable IDs and at most1000 tabs required")
    max_position, max_deformation, min_glue, clearance, bend, area_error = map(_q, (
        limits.max_position_mm, limits.max_differential_deformation,
        limits.min_glue_area_mm2, limits.clearance_mm, limits.bend_radius_mm,
        limits.area_uncertainty_mm2))
    if min(max_position, max_deformation, min_glue, area_error) <= 0:
        raise ValueError("Explicit positive geometric and glue budgets required")
    if min(clearance, bend) < 0:
        raise ValueError("Clearance and bend radius cannot be negative")
    thickness = None if limits.thickness_mm is None else _q(limits.thickness_mm)
    if thickness is not None and thickness < 0:
        raise ValueError("Thickness cannot be negative")
    required = (thickness or 0)+clearance+2*bend
    problems, rows, geometries, triangles = [], [], {}, {}
    budget = [max_cells]
    for tab in tabs:
        row = {"tab_id": tab.tab_id, "enabled": tab.enabled,
               "owner_id": tab.owner_id, "receiver_id": tab.receiver_id}
        rows.append(row)
        if type(tab.enabled) is not bool:
            raise ValueError("Enabled state must be boolean")
        if not tab.enabled:
            row["status"] = "OFF"
            continue
        try:
            if not all((rim.rim_id, rim.body_id, cap.part_id, tab.tab_id)):
                raise ValueError("Stable rim, body, receiver and tab identities required")
            if rim.body_id == cap.part_id:
                raise ValueError("Body owner and receiver cap must have distinct entity identities")
            if tab.owner_id != rim.body_id or tab.receiver_id != cap.part_id:
                raise ValueError("Tab owner or actual receiver reference does not match")
            if tab.contact_side != "back" or cap.contact_side != "front":
                raise ValueError("This inward-fold family requires tab back to cap front contact")
            if _q(cap.plane_offset_mm) != 0:
                raise ValueError("Actual receiver contact plane does not coincide with folded glue")
            g = _geometry(rim, tab)
            turn = _q(tab.center_turn) % 1
            distance_to_seam = (turn-_q(rim.seam_turn)) % 1
            distance_to_seam = min(distance_to_seam, 1-distance_to_seam)
            if 2*_pi()[1]*distance_to_seam < g["half_angle"][0]:
                problems.append(("INVALID", tab.tab_id,
                                 "Source interval crosses the longitudinal paper seam"))
            elif 2*_pi()[0]*distance_to_seam <= g["half_angle"][1]:
                problems.append(("UNRESOLVED", tab.tab_id,
                                 "Source-to-paper-seam separation not proved"))
            geometries[tab.tab_id] = (g, turn)
            triangles[tab.tab_id] = _global_triangle(g["glue_triangle_local"], turn)
            row.update(g)
            row["center_turn"] = turn
            self_gap = (2*_pi()[0]*g["radius"]-g["source_arc_length_bounds_mm"][1],
                        2*_pi()[1]*g["radius"]-g["source_arc_length_bounds_mm"][0])
            requested = _q(tab.requested_min_gap_mm)
            if requested < 0:
                raise ValueError("Requested source gap cannot be negative")
            row["source_period_gap_bounds_mm"] = self_gap
            if self_gap[1] < requested:
                problems.append(("INVALID", tab.tab_id, "Periodic self gap below explicit minimum"))
            elif self_gap[0] < requested:
                problems.append(("UNRESOLVED", tab.tab_id, "Periodic self gap minimum not proved"))
            low, high, outside = _contact(g["glue_triangle_local"], turn, cap,
                                          budget, max_depth, area_error)
            row["actual_glue_area_bounds_mm2"] = low, high
            row["proven_uncovered_glue_area_mm2"] = outside
            row["status"] = "BOUNDED"
            if outside > 0 or high < min_glue:
                problems.append(("INVALID", tab.tab_id,
                                 "Actual receiver lacks required glue material"))
            elif low < min_glue or low != high:
                problems.append(("UNRESOLVED", tab.tab_id,
                                 "Actual glue coverage is not fully proved"))
            if g["position_bound_mm"] > max_position:
                problems.append(("UNRESOLVED", tab.tab_id, "Collar position budget not proved"))
            if g["differential_deformation_bound"] > max_deformation:
                problems.append(("UNRESOLVED", tab.tab_id, "Collar deformation budget not proved"))
            if g["differential_deformation_bound"] >= 1:
                problems.append(("UNRESOLVED", tab.tab_id, "Local material regularity not proved"))
            if g["collar_injectivity_margin"] <= 0:
                problems.append(("UNRESOLVED", tab.tab_id,
                                 "Collar whole-domain injectivity not proved"))
            if g["body_distance_lower_mm"] <= required:
                problems.append(("UNRESOLVED", tab.tab_id,
                                 "Body separation outside relief not proved"))
            h = _sqrt(1-g["slope"]**2)[0]
            if g["relief"]*h <= (thickness or 0)*max(0, g["slope"]):
                problems.append(("UNRESOLVED", tab.tab_id,
                                 "Receiver one-sided fold envelope not proved"))
        except ValueError as exc:
            row["status"] = "INVALID"
            problems.append(("INVALID", tab.tab_id, str(exc)))
    pairs = []
    tab_by_id = {tab.tab_id: tab for tab in tabs}
    for first, second in combinations(geometries, 2):
        if len(pairs) >= max_pairs:
            problems.append(("UNRESOLVED", None, "Complete sibling pair budget exhausted"))
            break
        g1, turn1 = geometries[first]
        g2, turn2 = geometries[second]
        if _certain_overlap(triangles[first], triangles[second]):
            problems.append(("INVALID", (first, second),
                             "Certain positive-area sibling glue overlap"))
        distance_turn = abs(turn1-turn2)
        distance_turn = min(distance_turn, 1-distance_turn)
        source_gap = (g1["radius"]*(2*_pi()[0]*distance_turn
                      -g1["half_angle"][1]-g2["half_angle"][1]),
                      g1["radius"]*(2*_pi()[1]*distance_turn
                      -g1["half_angle"][0]-g2["half_angle"][0]))
        requested_gap = max(_q(tab_by_id[first].requested_min_gap_mm),
                            _q(tab_by_id[second].requested_min_gap_mm))
        if requested_gap < 0:
            raise ValueError("Requested source gap cannot be negative")
        if source_gap[1] < requested_gap:
            problems.append(("INVALID", (first, second), "Source gap below explicit minimum"))
        elif source_gap[0] < requested_gap:
            problems.append(("UNRESOLVED", (first, second), "Source gap minimum not proved"))
        delta = 2*_pi()[0]*distance_turn-g1["angular_sector_half_bound"]
        delta -= g2["angular_sector_half_bound"]
        radius = min(g1["radius"]-g1["depth"], g2["radius"]-g2["depth"])
        lower = 2*radius*(delta/2-(delta/2)**3/6) if delta > 0 else Fraction(0)
        lower -= g1["position_bound_mm"]+g2["position_bound_mm"]
        pairs.append({"tab_ids": (first, second),
                      "whole_phase_distance_lower_mm": _round((lower,)*2)[0],
                      "source_gap_bounds_mm": _round(source_gap)})
        if lower <= required:
            problems.append(("UNRESOLVED", (first, second),
                             "Whole-phase sibling separation not proved"))
    if thickness is None:
        problems.append(("UNVERIFIED", None, "Material thickness is unknown"))
    unresolved_obstacle_ids = tuple(unresolved_obstacle_ids)
    if unresolved_obstacle_ids:
        problems.append(("UNRESOLVED", unresolved_obstacle_ids,
                         "Other assembly barriers have no complete fold proof in this component"))
    if not geometries:
        problems.append(("UNRESOLVED", None, "No active supported tab material"))
    precedence = {"UNVERIFIED": 1, "UNRESOLVED": 2, "INVALID": 3}
    for row in rows:
        statuses = [p[0] for p in problems if p[1] == row["tab_id"]]
        if statuses:
            row["status"] = max(statuses, key=precedence.get)
    status = max((p[0] for p in problems), key=precedence.get, default="CERTIFIED_APPROXIMATE")
    return {"status": status, "method": "ATTACHED_NATIVE_BASE_WITH_DEFORMING_RELIEF_COLLAR",
            "scope": "ANALYTIC_OPEN_BODY_SIBLING_TABS_AND_DISK_RECEIVER_ONLY",
            "physical_status": "P3_NOT_RUN_NO_ELASTICITY_OR_ADHESIVE_CLAIM",
            "fold_scope": "ALL_INDEPENDENT_TAB_PHASES_FROM_GENERATOR_TO_INWARD_CAP",
            "contact_permission_scope": "BODY_AND_RECEIVER_WITHIN_EXPLICIT_UNGLUED_RELIEF_COLLAR",
            "requires_exact_shared_native_base_in_body_adapter": True,
            "unresolved_obstacle_ids": unresolved_obstacle_ids,
            "expected_active_pair_count": len(geometries)*(len(geometries)-1)//2,
            "expected_ids": tuple(t.tab_id for t in tabs),
            "checked_ids": tuple(geometries), "tabs": tuple(rows), "pairs": tuple(pairs),
            "problems": tuple(problems), "cells_used": max_cells-budget[0]}


def evaluate_tab(rim, tab, x, y, phase):
    """Preview only; phase0 is generator tangent, phase1 is folded onto cap."""
    g = _geometry(rim, tab)
    r, k = float(g["radius"]), float(g["slope"])
    x, y, phase = (float(_q(value)) for value in (x, y, phase))
    if not 0 <= phase <= 1 or abs(x) > float(g["xe"]):
        raise ValueError("Preview parameter is outside supported material coordinates")
    f = -k*x*x/r/(1+math.sqrt(1-(k*x/r)**2)) if k else 0
    theta = math.asin(k*x/r)/k if k else x/r
    beta = math.atan2(math.sqrt(1-k*k), -k)
    phi = phase*beta
    radial = k*math.cos(phi)-math.sqrt(1-k*k)*math.sin(phi)
    vertical = math.sqrt(1-k*k)*math.cos(phi)+k*math.sin(phi)
    alpha = max(0, (float(g["relief"])-y)/(float(g["relief"])-f))
    d = (r*math.cos(theta)-r-f*radial, r*math.sin(theta)-x, -f*vertical)
    local = (r+y*radial+alpha*d[0], x+alpha*d[1], y*vertical+alpha*d[2])
    angle = 2*math.pi*float(_q(tab.center_turn) % 1)
    return (local[0]*math.cos(angle)-local[1]*math.sin(angle),
            local[0]*math.sin(angle)+local[1]*math.cos(angle), local[2])
