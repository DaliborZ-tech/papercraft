"""Reversible author commands that preserve source sketches and unaffected work."""

from __future__ import annotations

from .errors import ValidationError
from .paper import part_input
from .project import atomic


def _part(project, identity):
    if not isinstance(identity, str) or identity not in project.parts:
        raise ValidationError("Vybraný papírový díl už v projektu není.")
    part = project.parts[identity]
    return {"id": part.id, "name": part.name, "number": part.number}


def _surface(project, identity):
    if not isinstance(identity, str) or identity not in project.surfaces:
        raise ValidationError("Vybraná plocha už v projektu není.")
    surface = project.surfaces[identity]
    return {"id": identity, "name": surface.name, "part": _part(project, surface.part_id)}


def part_deletion_impact(project, part_id):
    """Return concrete removal/retention records without validating or changing state."""
    part = _part(project, part_id)
    removed = set(project.parts[part_id].surface_ids)
    surfaces = [_surface(project, sid) for sid in project.parts[part_id].surface_ids]
    joints, attachments, connector_ids, neighbors = [], [], set(), set()
    for collection, output, kind in (
        (project.joints, joints, "joint"),
        (project.attachments, attachments, "attachment"),
    ):
        for record in collection.values():
            a, b = (
                (record.surface_a, record.surface_b)
                if kind == "joint"
                else (record.source_surface_id, record.target_surface_id)
            )
            if not removed.intersection((a, b)):
                continue
            other = [sid for sid in (a, b) if sid not in removed]
            neighbors.update(project.surfaces[sid].part_id for sid in other)
            if record.connector_id:
                connector_ids.add(record.connector_id)
            output.append(
                {
                    "id": record.id,
                    "number": record.number,
                    "kind": record.mode if kind == "joint" else record.kind,
                    "surfaces": [_surface(project, a), _surface(project, b)],
                    "counterparts": [_surface(project, sid) for sid in other],
                    "connector_id": record.connector_id,
                    "unresolved": record.unresolved,
                }
            )
    profiles = []
    used = set()
    for sid in project.parts[part_id].surface_ids:
        surface = project.surfaces[sid]
        for pid in [surface.profile_id, *surface.hole_profile_ids]:
            if pid not in used:
                used.add(pid)
                profiles.append({"id": pid, "name": project.profiles[pid].name})
    return {
        "project_id": project.project_id,
        "project_revision": project.revision,
        "part": part,
        "surfaces": surfaces,
        "preserved_profiles": profiles,
        "joints": joints,
        "attachments": attachments,
        "connectors": [
            {
                "id": cid,
                "owner": _surface(project, project.connectors[cid].owner_surface_id),
                "tab_count": project.connectors[cid].count,
            }
            for cid in sorted(connector_ids)
        ],
        "affected_parts": [_part(project, pid) for pid in sorted(neighbors)],
    }


def _invalidate_changed_caches(project):
    # The existing dependency digest includes neighbors' printed relations. This
    # also catches an indirectly dependent cache without recomputing geometry or
    # requiring some other unresolved joint/anchor to be repaired first.
    for part in project.parts.values():
        if part.input_digest != part_input(project, part):
            part.stale = True


@atomic
def delete_material_part(project, part_id):
    """Delete exactly one material component; profiles and monotonic counters stay."""
    impact = part_deletion_impact(project, part_id)
    for relation in impact["joints"]:
        del project.joints[relation["id"]]
    for relation in impact["attachments"]:
        del project.attachments[relation["id"]]
    for connector in impact["connectors"]:
        del project.connectors[connector["id"]]
    for surface in impact["surfaces"]:
        del project.surfaces[surface["id"]]
    del project.placements[part_id]
    del project.parts[part_id]
    project.revision += 1
    _invalidate_changed_caches(project)
    return impact


def _name(value):
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValidationError("Název musí obsahovat viditelný text bez řídicích znaků.")
    return value


@atomic
def rename_author_entities(
    project, *, project_name=None, surface_id=None, surface_name=None, part_id=None, part_name=None
):
    """Rename only requested entities, without changing geometry, identities or placement."""
    changes = []
    if project_name is not None:
        changes.append((project, _name(project_name)))
    if surface_name is not None:
        _surface(project, surface_id)
        changes.append((project.surfaces[surface_id], _name(surface_name)))
    elif surface_id is not None:
        _surface(project, surface_id)
    if part_name is not None:
        _part(project, part_id)
        changes.append((project.parts[part_id], _name(part_name)))
    elif part_id is not None:
        _part(project, part_id)
    changed = [(record, value) for record, value in changes if record.name != value]
    if not changed:
        return
    for record, value in changed:
        record.name = value
    project.revision += 1
    _invalidate_changed_caches(project)
