"""Persistent authoring identities, source curves and paper state."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import numpy as np

from .errors import ValidationError
from .geometry import number, vector


def identity():
    return str(uuid4())


def uuid(value):
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Očekáváno stabilní UUID.") from exc
    return value


@dataclass
class SketchPlane:
    origin: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    u: list[float] = field(default_factory=lambda: [1.0, 0.0, 0.0])
    v: list[float] = field(default_factory=lambda: [0.0, 1.0, 0.0])

    def validate(self):
        self.origin = vector(self.origin, 3)
        self.u, self.v = vector(self.u, 3), vector(self.v, 3)
        if not (
            math.isclose(np.linalg.norm(self.u), 1, abs_tol=1e-12)
            and math.isclose(np.linalg.norm(self.v), 1, abs_tol=1e-12)
            and abs(np.dot(self.u, self.v)) < 1e-12
        ):
            raise ValidationError("Pracovní rovina potřebuje dvě kolmé jednotkové osy.")

    @classmethod
    def named(cls, name):
        choices = {
            "XY": cls(),
            "XZ": cls(v=[0.0, 0.0, 1.0]),
            "YZ": cls(u=[0.0, 1.0, 0.0], v=[0.0, 0.0, 1.0]),
        }
        if name not in choices:
            raise ValidationError("Neznámá pracovní rovina.")
        return choices[name]

    def world(self, points):
        points = np.asarray(points, dtype=float)
        return np.asarray(self.origin) + points[:, :1] * self.u + points[:, 1:] * self.v


@dataclass
class Vertex:
    id: str
    point: list[float]


@dataclass
class CurveSegment:
    id: str
    kind: str
    start_vertex_id: str
    end_vertex_id: str
    data: dict = field(default_factory=dict)


@dataclass
class Profile:
    id: str
    name: str
    vertices: list[Vertex]
    segments: list[CurveSegment]
    closed: bool = True
    plane: SketchPlane = field(default_factory=SketchPlane)
    revision: int = 1

    @property
    def points(self):
        return [copy.deepcopy(vertex.point) for vertex in self.vertices]

    def vertex(self, vertex_id):
        return next((v for v in self.vertices if v.id == vertex_id), None)

    def segment(self, segment_id):
        return next((s for s in self.segments if s.id == segment_id), None)

    def validate(self):
        uuid(self.id)
        if (
            not isinstance(self.name, str)
            or not isinstance(self.closed, bool)
            or type(self.revision) is not int
            or self.revision < 1
        ):
            raise ValidationError("Neplatná metadata profilu.")
        self.plane.validate()
        if len(self.vertices) < (3 if self.closed else 2):
            raise ValidationError("Profil má příliš málo bodů.")
        ids = [v.id for v in self.vertices]
        if len(set(ids)) != len(ids) or len(self.segments) != len(ids) - (0 if self.closed else 1):
            raise ValidationError("Profil nemá úplnou uspořádanou topologii.")
        for vertex in self.vertices:
            uuid(vertex.id)
            vertex.point = vector(vertex.point, 2)
        for index, segment in enumerate(self.segments):
            uuid(segment.id)
            if (
                segment.start_vertex_id != ids[index]
                or segment.end_vertex_id != ids[(index + 1) % len(ids)]
            ):
                raise ValidationError("Segment nenavazuje na své vrcholy.")
            a, b = self.vertices[index].point, self.vertices[(index + 1) % len(ids)].point
            if np.linalg.norm(np.asarray(b) - a) <= 1e-9:
                raise ValidationError("Profil obsahuje nulový segment.")
            if segment.kind == "line":
                if segment.data != {}:
                    raise ValidationError("Úsečka neobsahuje další neznámé parametry.")
            elif segment.kind == "arc":
                if set(segment.data) != {"center", "sweep_deg"}:
                    raise ValidationError("Oblouk potřebuje střed a orientovaný úhel.")
                center = vector(segment.data["center"], 2)
                sweep = number(segment.data["sweep_deg"], "Úhel oblouku")
                if not 0 < abs(sweep) < 360:
                    raise ValidationError("Oblouk potřebuje nenulový úhel menší než celý obvod.")
                radius = np.asarray(a) - center
                angle = math.radians(sweep)
                end = (
                    np.asarray(center)
                    + np.array(
                        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
                    )
                    @ radius
                )
                if np.linalg.norm(radius) <= 1e-9 or not np.allclose(end, b, atol=1e-7, rtol=0):
                    raise ValidationError("Koncový bod neodpovídá oblouku.")
            elif segment.kind == "cubic":
                if set(segment.data) != {"control1", "control2"}:
                    raise ValidationError("Kubická křivka potřebuje dva řídicí body.")
                vector(segment.data["control1"], 2)
                vector(segment.data["control2"], 2)
            else:
                raise ValidationError("Nepodporovaný typ zdrojové křivky.")


@dataclass
class SurfaceFeature:
    id: str
    name: str
    profile_id: str
    hole_profile_ids: list[str] = field(default_factory=list)
    kind: str = "planar"
    params: dict = field(default_factory=dict)
    position_mm: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_deg: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    parent_transforms: list = field(default_factory=list)
    revision: int = 1
    part_id: str = ""


@dataclass
class PaperFrame:
    root_surface_id: str
    anchor_vertex_id: str
    axis_segment_id: str


@dataclass
class MaterialPart:
    id: str
    name: str
    surface_ids: list[str]
    frame: PaperFrame
    stale: bool = True
    source_revision: int = 0
    input_digest: str = ""
    polygons: dict = field(default_factory=dict)
    paths: dict = field(default_factory=dict)
    labels: list = field(default_factory=list)
    lineage: list[str] = field(default_factory=list)
    front_side: str = "outside"
    edges: list = field(default_factory=list)
    number: int = 1


@dataclass
class Page:
    id: str = field(default_factory=identity)
    width_mm: float = 210.0
    height_mm: float = 297.0
    margin_mm: float = 10.0


@dataclass
class Placement:
    page_id: str | None = None
    x_mm: float = 0.0
    y_mm: float = 0.0
    rotation_deg: float = 0.0
    position_locked: bool = False
    rotation_locked: bool = False


@dataclass
class Joint:
    id: str
    surface_a: str
    edge_a: str
    surface_b: str
    edge_b: str
    mode: str = "cut"
    revision: int = 1
    connector_id: str | None = None
    number: int = 1
    unresolved: bool = False


@dataclass
class Connector:
    id: str
    joint_id: str
    owner_surface_id: str
    width_mm: float = 5.0
    taper: float = 0.6
    shape: str = "trapezoid"
    revision: int = 1


@dataclass(frozen=True)
class Issue:
    id: str
    code: str
    severity: str
    message: str
    part_ids: tuple[str, ...] = ()
    joint_id: str | None = None
    digest: str = ""
    acknowledged: bool = False
