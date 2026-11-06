"""Author commands for interior contact, independent glue regions and connectors."""

from __future__ import annotations

import copy
import math
import warnings

import numpy as np
from scipy.spatial.transform import Rotation

from .attachments import (
    attachment_geometry,
    connector_shapes,
    edge_source,
    interval_points,
    source_outward,
    surface_basis,
    trace_connector_contact,
    world_to_uv,
)
from .commands import atomic
from .errors import ValidationError
from .geometry import material_polygon, number, validate_rigid, vector
from .model import Attachment, Connector, identity, uuid


class InteriorCommands:
    def _validate_interior(self, connector_ids):
        ids, numbers = [], set()
        if type(self.next_attachment_number) is not int or self.next_attachment_number < 1:
            raise ValidationError("Neplatný čítač vnitřních spojů.")
        for aid, record in self.attachments.items():
            uuid(aid)
            ids.append(aid)
            if (
                record.id != aid
                or record.kind not in ("surface_trace", "glue_region")
                or record.source_surface_id not in self.surfaces
                or record.target_surface_id not in self.surfaces
                or record.source_surface_id == record.target_surface_id
                or record.target_side not in ("inside", "outside")
                or type(record.glue_direction) is not int
                or record.glue_direction not in (-1, 1)
                or not isinstance(record.unresolved, bool)
                or type(record.revision) is not int
                or record.revision < 1
                or type(record.number) is not int
                or not 0 < record.number < self.next_attachment_number
                or record.number in numbers
                or not isinstance(record.requested_placement, dict)
                or not isinstance(record.source_region_uv, list)
                or not isinstance(record.target_region_uv, list)
            ):
                raise ValidationError("Neplatný vnitřní konstrukční spoj.")
            numbers.add(record.number)
            if record.source_edge_id is not None:
                uuid(record.source_edge_id)
                interval = vector(record.source_interval, 2)
                if not 0 <= interval[0] < interval[1] <= 1:
                    raise ValidationError("Neplatný interval vnitřního spoje.")
                if not record.unresolved:
                    edge_source(self, record.source_surface_id, record.source_edge_id)
                if record.source_region_uv or (
                    record.kind == "surface_trace" and record.target_region_uv
                ):
                    raise ValidationError("Čárová stopa se nezaměňuje za lepicí oblast.")
                if record.kind == "glue_region":
                    material_polygon(record.target_region_uv)
            else:
                if record.kind != "glue_region" or record.connector_id:
                    raise ValidationError("Lepicí oblast nemá hranu chlopně.")
                material_polygon(record.target_region_uv)
                if record.source_region_uv:
                    material_polygon(record.source_region_uv)
            if record.requested_placement:
                if set(record.requested_placement) != {
                    "target_start_uv",
                    "target_end_uv",
                    "angle_deg",
                    "target_matrix",
                }:
                    raise ValidationError("Neplatné zadané umístění spoje.")
                vector(record.requested_placement["target_start_uv"], 2)
                vector(record.requested_placement["target_end_uv"], 2)
                number(record.requested_placement["angle_deg"])
                validate_rigid(record.requested_placement["target_matrix"])
            if record.connector_id:
                if record.connector_id not in self.connectors:
                    raise ValidationError("Chybí chlopeň vnitřního spoje.")
                connector_ids.append(record.connector_id)
        return ids

    def attachment_geometry(self, attachment_id):
        attachment = self.attachments[attachment_id]
        try:
            result = attachment_geometry(self, attachment)
            result.update(valid=True, issues=[])
            if attachment.connector_id:
                result["tabs"] = trace_connector_contact(
                    self, attachment, self.connectors[attachment.connector_id]
                )
                for tab in result["tabs"]:
                    if tab["nominal_area_mm2"] - tab["available_area_mm2"] > max(
                        1e-8, tab["nominal_area_mm2"] * 1e-10
                    ):
                        result["valid"] = False
                        result["issues"].append(
                            "FOLDED_GLUE_AREA_PARTIAL: záložka zasahuje mimo "
                            "lepicí materiál nebo do otvoru."
                        )
            return copy.deepcopy(result)
        except ValidationError as exc:
            return {
                "valid": False,
                "issues": [str(exc)],
                "kind": attachment.kind,
                "receiver_surface_id": attachment.target_surface_id,
            }

    @atomic
    def attach_edge_to_surface(
        self,
        source_sid,
        edge_id,
        target_sid,
        *,
        interval=(0, 1),
        target_side="inside",
        glue_direction=1,
        requested_placement=None,
    ):
        if source_sid == target_sid:
            raise ValidationError("Připojení potřebuje dva různé materiálové povrchy.")
        record = Attachment(
            identity(),
            "surface_trace",
            source_sid,
            target_sid,
            source_edge_id=edge_id,
            source_interval=list(interval),
            target_side=target_side,
            glue_direction=glue_direction,
            requested_placement=copy.deepcopy(requested_placement or {}),
            number=self.next_attachment_number,
        )
        # Creation is strict; later explicit edits can leave a diagnosable stale relation.
        attachment_geometry(self, record)
        for other in self.attachments.values():
            if (
                other.kind == "surface_trace"
                and other.source_surface_id == source_sid
                and other.source_edge_id == edge_id
                and max(other.source_interval[0], interval[0])
                < min(other.source_interval[1], interval[1]) - 1e-12
            ):
                raise ValidationError(
                    "Zdrojový interval již má připojení. Upravte existující spoj."
                )
        self.next_attachment_number += 1
        self.attachments[record.id] = record
        self._touch((source_sid, target_sid))
        self.recompute({self.part_for_surface(source_sid), self.part_for_surface(target_sid)})
        return record.id

    def preview_attachment(
        self,
        source_sid,
        edge_id,
        target_sid,
        target_start_uv,
        target_end_uv,
        *,
        angle_deg=90,
        interval=(0, 1),
        target_side="inside",
        glue_direction=1,
    ):
        """The same atomic command runs on a clone; cancel never changes the live document."""
        clone = type(self).from_dict(self.to_dict())
        try:
            aid = clone.place_and_attach_edge(
                source_sid,
                edge_id,
                target_sid,
                target_start_uv,
                target_end_uv,
                angle_deg=angle_deg,
                interval=interval,
                target_side=target_side,
                glue_direction=glue_direction,
            )
            return {
                "valid": True,
                "issues": [],
                "attachment_id": aid,
                "geometry": clone.attachment_geometry(aid),
                "placement": {
                    "position_mm": clone.surfaces[source_sid].position_mm,
                    "rotation_deg": clone.surfaces[source_sid].rotation_deg,
                },
                "world_geometry": clone.world_geometry(source_sid),
                "project_state": clone.to_dict(),
            }
        except ValidationError as exc:
            return {"valid": False, "issues": [str(exc)], "geometry": None}

    preview_edge_attachment = preview_attachment

    @atomic
    def place_and_attach_edge(
        self,
        source_sid,
        edge_id,
        target_sid,
        target_start_uv,
        target_end_uv,
        *,
        angle_deg=90,
        interval=(0, 1),
        target_side="inside",
        glue_direction=1,
    ):
        if source_sid == target_sid:
            raise ValidationError("Vyberte zdrojovou hranu a jinou cílovou plochu.")
        if any(source_sid in (j.surface_a, j.surface_b) for j in self.joints.values()) or any(
            source_sid in (a.source_surface_id, a.target_surface_id)
            for a in self.attachments.values()
        ):
            raise ValidationError("Přesouvaná plocha již má spoje; nejprve je výslovně upravte.")
        start, end = vector(target_start_uv, 2), vector(target_end_uv, 2)
        temporary = Attachment(
            identity(),
            "surface_trace",
            source_sid,
            target_sid,
            source_edge_id=edge_id,
            source_interval=list(interval),
        )
        local = interval_points(self, temporary)
        source = self._surface_world_points(source_sid, local)
        target = self._surface_world_points(target_sid, [start, end])
        length, target_length = math.dist(*source), math.dist(*target)
        if target_length <= 1e-9 or abs(length - target_length) > max(1e-6, length * 1e-9):
            raise ValidationError("Nakreslená připojovací čára nemá délku zdrojového intervalu.")
        angle = number(angle_deg, "Úhel připojení")
        source_x, target_x = (source[1] - source[0]) / length, (target[1] - target[0]) / length
        source_n = np.asarray(self.world_geometry(source_sid)["normal"])
        target_n = np.asarray(self.world_geometry(target_sid)["normal"])
        desired_n = Rotation.from_rotvec(target_x * math.radians(angle)).apply(target_n)
        current = np.column_stack([source_x, np.cross(source_n, source_x), source_n])
        desired = np.column_stack([target_x, np.cross(desired_n, target_x), desired_n])
        incremental = np.eye(4)
        incremental[:3, :3] = desired @ current.T
        incremental[:3, 3] = target[0] - incremental[:3, :3] @ source[0]
        surface = self.surfaces[source_sid]
        parent = np.eye(4)
        for matrix in surface.parent_transforms:
            parent = parent @ validate_rigid(matrix)
        placed = np.linalg.inv(parent) @ incremental @ self._surface_matrix(source_sid)
        validate_rigid(placed)
        surface.position_mm = placed[:3, 3].tolist()
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="Gimbal lock detected.*", category=UserWarning
            )
            surface.rotation_deg = (
                Rotation.from_matrix(placed[:3, :3]).as_euler("xyz", degrees=True).tolist()
            )
        self._touch([source_sid])
        return self.attach_edge_to_surface(
            source_sid,
            edge_id,
            target_sid,
            interval=interval,
            target_side=target_side,
            glue_direction=glue_direction,
            requested_placement={
                "target_start_uv": start,
                "target_end_uv": end,
                "angle_deg": angle,
                "target_matrix": self._surface_matrix(target_sid).tolist(),
            },
        )

    @atomic
    def set_glue_region(
        self,
        source_sid,
        target_sid,
        target_outline_uv,
        *,
        source_outline_uv=None,
        source_edge_id=None,
        interval=(0, 1),
        target_side="inside",
        glue_direction=1,
    ):
        if source_sid == target_sid:
            raise ValidationError("Lepicí oblast potřebuje samostatný protikus.")
        record = Attachment(
            identity(),
            "glue_region",
            source_sid,
            target_sid,
            target_region_uv=[vector(p, 2) for p in target_outline_uv],
            source_region_uv=[]
            if source_outline_uv is None
            else [vector(p, 2) for p in source_outline_uv],
            target_side=target_side,
            number=self.next_attachment_number,
            source_edge_id=source_edge_id,
            source_interval=list(interval),
            glue_direction=glue_direction,
        )
        attachment_geometry(self, record)
        self.next_attachment_number += 1
        self.attachments[record.id] = record
        self._touch((source_sid, target_sid))
        self.recompute({self.part_for_surface(source_sid), self.part_for_surface(target_sid)})
        return record.id

    add_glue_region = set_glue_region

    @atomic
    def update_attachment(
        self,
        attachment_id,
        *,
        target_side=None,
        glue_direction=None,
        source_edge_id=None,
        interval=None,
        target_region_uv=None,
    ):
        record = self.attachments[attachment_id]
        if target_side is not None:
            record.target_side = target_side
        if glue_direction is not None:
            record.glue_direction = glue_direction
        if source_edge_id is not None:
            record.source_edge_id, record.unresolved = source_edge_id, False
        if interval is not None:
            record.source_interval = list(interval)
        if target_region_uv is not None:
            record.target_region_uv = [vector(p, 2) for p in target_region_uv]
            record.kind = "glue_region"
        attachment_geometry(self, record)
        record.revision += 1
        self._touch((record.source_surface_id, record.target_surface_id))
        # Repair the reference before asking the paper engine to resolve other,
        # independently missing anchors. Explicit recompute follows the repairs.

    @atomic
    def remove_attachment(self, attachment_id):
        record = self.attachments.pop(attachment_id)
        if record.connector_id:
            del self.connectors[record.connector_id]
        self._touch((record.source_surface_id, record.target_surface_id))
        # Removal must stay possible while another independent reference or
        # anchor is unresolved. Old paper remains visibly stale until recompute.

    @atomic
    def set_attachment_tab(
        self,
        attachment_id,
        *,
        width_mm=None,
        taper=None,
        shape=None,
        count=None,
        gap_mm=None,
        outline_mm=None,
    ):
        record = self.attachments[attachment_id]
        if record.source_edge_id is None:
            raise ValidationError("Plošné lepení nepřidává novou chlopeň bez hrany ohybu.")
        if record.connector_id is None:
            connector = Connector(identity(), "", record.source_surface_id, attachment_id=record.id)
            record.connector_id = connector.id
            self.connectors[connector.id] = connector
        self.set_connector(
            record.connector_id,
            width_mm=width_mm,
            taper=taper,
            shape=shape,
            count=count,
            gap_mm=gap_mm,
            outline_mm=outline_mm,
        )
        return record.connector_id

    @atomic
    def set_connector(
        self,
        connector_id,
        *,
        width_mm=None,
        taper=None,
        shape=None,
        count=None,
        gap_mm=None,
        outline_mm=None,
        enabled=None,
        owner=None,
    ):
        connector = self.connectors[connector_id]
        if count is not None and (type(count) is not int or not 1 <= count <= 4096):
            raise ValidationError("Počet záložek musí být celé číslo1 až4096.")
        for key, value in {
            "width_mm": width_mm,
            "taper": taper,
            "shape": shape,
            "count": count,
            "gap_mm": gap_mm,
            "enabled": enabled,
        }.items():
            if value is not None:
                setattr(connector, key, value)
        if outline_mm is not None:
            connector.outline_mm = [vector(p, 2) for p in outline_mm]
        if owner is not None:
            if (
                connector.attachment_id
                and owner != self.attachments[connector.attachment_id].source_surface_id
            ):
                raise ValidationError(
                    "Uvnitř souvislého protikusu nelze vytvořit chlopeň bez řezu. Použijte pásek."
                )
            connector.owner_surface_id = owner
        while len(connector.tab_ids) < connector.count:
            connector.tab_ids.append(identity())
        connector.tab_ids = connector.tab_ids[: connector.count]
        connector.tab_overrides = {
            k: v for k, v in connector.tab_overrides.items() if k in connector.tab_ids
        }
        connector.revision += 1
        source, target = self._connector_surfaces(connector)
        self.validate()
        if connector.attachment_id:
            for tab in trace_connector_contact(
                self, self.attachments[connector.attachment_id], connector
            ):
                if tab["nominal_area_mm2"] - tab["available_area_mm2"] > max(
                    1e-8, tab["nominal_area_mm2"] * 1e-10
                ):
                    raise ValidationError(
                        "FOLDED_GLUE_AREA_PARTIAL: záložka není celá na materiálu protikusu."
                    )
        self._touch((source, target))
        self.recompute({self.part_for_surface(source), self.part_for_surface(target)})

    @atomic
    def set_connector_tab(self, connector_id, tab_id, **changes):
        connector = self.connectors[connector_id]
        if tab_id not in connector.tab_ids:
            raise ValidationError("Zvolená záložka již neexistuje; nepoužívá se náhradní index.")
        if set(changes) - {"enabled", "width_mm", "taper", "shape", "outline_mm"}:
            raise ValidationError("Neznámá úprava záložky.")
        connector.tab_overrides.setdefault(tab_id, {}).update(copy.deepcopy(changes))
        self.set_connector(connector_id)

    def _connector_surfaces(self, connector):
        if connector.attachment_id:
            record = self.attachments[connector.attachment_id]
            return record.source_surface_id, record.target_surface_id
        joint = self.joints[connector.joint_id]
        return joint.surface_a, joint.surface_b

    def connector_geometry(self, connector_id):
        try:
            result = self._connector_geometry(connector_id)
            result.update(valid=True, issues=[])
            return result
        except ValidationError as exc:
            connector = self.connectors[connector_id]
            return {
                "connector_id": connector_id,
                "valid": False,
                "issues": [str(exc)],
                "tab_ids": list(connector.tab_ids),
                "tabs": [],
                "all_tabs": [
                    {
                        "id": tid,
                        "enabled": connector.enabled
                        and connector.tab_overrides.get(tid, {}).get("enabled", True),
                        "outline_mm": [],
                        "base_length_mm": None,
                        "source_interval": None,
                        "folded_contact": None,
                    }
                    for tid in connector.tab_ids
                ],
                "hinge_length_mm": None,
                "tab_length_mm": None,
                "standalone_part_id": None,
                "enabled": connector.enabled,
                "clearance_status": "MATERIAL_CLEARANCE_UNVERIFIED",
                "bend_sweep_status": "NOT_CHECKED",
            }

    def _connector_geometry(self, connector_id):
        from .paper import connector_contact

        connector = self.connectors[connector_id]
        if connector.attachment_id:
            attachment = self.attachments[connector.attachment_id]
            tabs = trace_connector_contact(self, attachment, connector)
            source = interval_points(self, attachment)
            source_interval = attachment.source_interval
        else:
            joint = self.joints[connector.joint_id]
            tabs = connector_contact(self, joint, connector)["tabs"]
            edge = joint.edge_a if connector.owner_surface_id == joint.surface_a else joint.edge_b
            source = edge_source(self, connector.owner_surface_id, edge)[2]
            source_interval = [0, 1]
        length = math.dist(*source) * self.scale
        pitch = length / connector.count
        base_length = pitch - connector.gap_mm
        generator = copy.deepcopy(connector)
        generator.enabled = True
        for change in generator.tab_overrides.values():
            change["enabled"] = True
        all_tabs = []
        try:
            shapes = connector_shapes(generator, length)
        except ValidationError:
            shapes = []
        by_id = {shape["id"]: shape for shape in shapes}
        contacts = {tab["tab_id"]: tab for tab in tabs}
        for index, tab_id in enumerate(connector.tab_ids or [connector.id]):
            enabled = connector.enabled and connector.tab_overrides.get(tab_id, {}).get(
                "enabled", True
            )
            start = (index * pitch + connector.gap_mm / 2) / length
            end = ((index + 1) * pitch - connector.gap_mm / 2) / length
            original_start, original_end = source_interval
            descriptor = {
                "id": tab_id,
                "enabled": enabled,
                "base_length_mm": base_length,
                "source_interval": [
                    original_start + start * (original_end - original_start),
                    original_start + end * (original_end - original_start),
                ],
                "outline_mm": (by_id[tab_id]["points"] - [start * length, 0]).tolist()
                if tab_id in by_id
                else [],
                "folded_contact": copy.deepcopy(contacts.get(tab_id)),
            }
            all_tabs.append(descriptor)
        return {
            "connector_id": connector.id,
            "tab_ids": list(connector.tab_ids),
            "enabled": connector.enabled,
            "tabs": copy.deepcopy(tabs),
            "hinge_length_mm": length,
            "tab_length_mm": base_length,
            "all_tabs": all_tabs,
            "standalone_part_id": None,
            "clearance_status": "MATERIAL_CLEARANCE_UNVERIFIED",
            "bend_sweep_status": "NOT_CHECKED",
        }

    @atomic
    def remove_connector(self, connector_id):
        connector = self.connectors.pop(connector_id)
        source, target = self._connector_surfaces(connector)
        if connector.attachment_id:
            self.attachments[connector.attachment_id].connector_id = None
        else:
            self.joints[connector.joint_id].connector_id = None
        self._touch((source, target))

    @atomic
    def add_glue_band(
        self, attachment_id, *, width_mm=5, name="Lepicí pásek", source_side="inside"
    ):
        """Two real material flanges, a true fold and explicit glue receivers on both faces."""
        record = self.attachments[attachment_id]
        if record.kind != "surface_trace" or record.connector_id:
            raise ValidationError("Pásek potřebuje přímý spoj bez další aktivní chlopně.")
        data = attachment_geometry(self, record)
        world = np.asarray(data["source_world"])
        length = math.dist(*world)
        width = number(width_mm, "Šířka poloviny pásku", positive=True) / self.scale
        x = (world[1] - world[0]) / length
        source = record.source_surface_id
        _, outward = source_outward(self, source, record.source_edge_id)
        _, u, v = surface_basis(self, source)
        inward_world = -(outward[0] * u + outward[1] * v)
        target_uv = np.asarray(data["target_uv"])
        tangent = (target_uv[1] - target_uv[0]) / math.dist(*target_uv)
        inward_uv = np.array([-tangent[1], tangent[0]]) * record.glue_direction
        _, tu, tv = surface_basis(self, record.target_surface_id)
        target_inward = inward_uv[0] * tu + inward_uv[1] * tv
        first = self.add_profile(
            [[0, 0], [length, 0], [length, width], [0, width]],
            name=name + " · zdroj",
            plane={"origin": world[0].tolist(), "u": x.tolist(), "v": inward_world.tolist()},
        )
        second = self.add_profile(
            [[length, 0], [0, 0], [0, -width], [length, -width]],
            name=name + " · protikus",
            plane={"origin": world[0].tolist(), "u": x.tolist(), "v": (-target_inward).tolist()},
        )
        a, b = (
            self.add_surface(first, name=name),
            self.add_surface(second, name=name + " · protikus"),
        )
        jid = self.connect_edges(
            a, self.profiles[first].segments[0].id, b, self.profiles[second].segments[0].id
        )
        self.set_joint(jid, mode="fold", receiving_part_id=self.part_for_surface(a))
        for sid, receiver, side in [
            (a, source, source_side),
            (b, record.target_surface_id, record.target_side),
        ]:
            polygon = self.profiles[self.surfaces[sid].profile_id].points
            footprint, _ = world_to_uv(self, receiver, self._surface_world_points(sid, polygon))
            self.set_glue_region(sid, receiver, footprint.tolist(), target_side=side)
        return self.part_for_surface(a)
