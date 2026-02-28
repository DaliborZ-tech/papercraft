"""Hierarchie uzlů grafu scény."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.scene_graph.transform import Transform


class NodeType(Enum):
    """Podporované typy uzlů / objektů."""

    GROUP = auto()
    PRIMITIVE_BOX = auto()
    PRIMITIVE_CYLINDER = auto()
    PRIMITIVE_CONE = auto()
    PRIMITIVE_SPHERE = auto()
    PRIMITIVE_TORUS = auto()
    WALL = auto()
    OPENING = auto()
    ROOF = auto()
    GOTHIC_WINDOW = auto()
    ONION_DOME = auto()
    FLOOR_SLAB = auto()
    TOWER = auto()
    BUTTRESS = auto()
    CUSTOM_MESH = auto()


@dataclass
class SceneNode:
    """Jeden uzel v hierarchii scény.

    Každý uzel vlastní *transform*, slovník *parameters* (typově specifický),
    a volitelně cachovanou *mesh*.
    """

    name: str
    node_type: NodeType = NodeType.GROUP
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    transform: Transform = field(default_factory=Transform)
    parameters: dict[str, Any] = field(default_factory=dict)

    # Cachovaná mesh (generovaná z parametrů na vyžádání)
    _mesh: MeshData | None = field(default=None, repr=False)

    # OCC tvar (když je aktivní OCC back-end)
    _occ_shape: Any = field(default=None, repr=False)

    # Hierarchie
    parent: SceneNode | None = field(default=None, repr=False)
    children: list[SceneNode] = field(default_factory=list, repr=False)

    # Dirty příznak → regenerovat mesh
    _dirty: bool = True

    # Viditelnost, zamčení, izolace, vrstva
    visible: bool = True
    locked: bool = False
    isolated: bool = False
    layer: str = "default"

    # ── tree operations ────────────────────────────────────────────────

    def add_child(self, child: SceneNode) -> None:
        child.parent = self
        self.children.append(child)

    def remove_child(self, child: SceneNode) -> None:
        child.parent = None
        self.children.remove(child)

    def find_by_id(self, node_id: str) -> SceneNode | None:
        if self.node_id == node_id:
            return self
        for c in self.children:
            found = c.find_by_id(node_id)
            if found:
                return found
        return None

    def all_nodes(self) -> list[SceneNode]:
        """Return a flat list of this node and all descendants."""
        result = [self]
        for c in self.children:
            result.extend(c.all_nodes())
        return result

    # ── mesh access ────────────────────────────────────────────────────

    @property
    def mesh(self) -> MeshData | None:
        return self._mesh

    @mesh.setter
    def mesh(self, value: MeshData | None) -> None:
        self._mesh = value
        self._dirty = False

    def mark_dirty(self) -> None:
        self._dirty = True
        for c in self.children:
            c.mark_dirty()

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    # ── parameter helpers ──────────────────────────────────────────────

    def set_param(self, key: str, value: Any) -> None:
        self.parameters[key] = value
        self._dirty = True

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.parameters.get(key, default)

    # ── viditelnost / zamčení ───────────────────────────────────────────

    def set_visible(self, visible: bool, recursive: bool = False) -> None:
        """Nastav viditelnost. Pokud recursive, aplikuj na potomky."""
        self.visible = visible
        if recursive:
            for c in self.children:
                c.set_visible(visible, recursive=True)

    def set_locked(self, locked: bool, recursive: bool = False) -> None:
        """Zamkni/odemkni uzel."""
        self.locked = locked
        if recursive:
            for c in self.children:
                c.set_locked(locked, recursive=True)

    def isolate(self) -> None:
        """Izoluj tento uzel — skryj všechny sourozence."""
        self.isolated = True
        if self.parent:
            for sibling in self.parent.children:
                if sibling is not self:
                    sibling.set_visible(False, recursive=True)

    def unisolate(self) -> None:
        """Zruš izolaci — zobraz všechny sourozence."""
        self.isolated = False
        if self.parent:
            for sibling in self.parent.children:
                sibling.set_visible(True, recursive=True)

    def visible_nodes(self) -> list[SceneNode]:
        """Vrátí všechny viditelné uzly v podstromu."""
        result: list[SceneNode] = []
        if self.visible:
            result.append(self)
        for c in self.children:
            result.extend(c.visible_nodes())
        return result

    # ── repr ───────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"SceneNode(name={self.name!r}, type={self.node_type.name}, "
            f"children={len(self.children)})"
        )
