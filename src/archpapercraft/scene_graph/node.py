"""Scene-graph node hierarchy."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.scene_graph.transform import Transform


class NodeType(Enum):
    """Supported node / object types."""

    GROUP = auto()
    PRIMITIVE_BOX = auto()
    PRIMITIVE_CYLINDER = auto()
    PRIMITIVE_CONE = auto()
    WALL = auto()
    OPENING = auto()
    ROOF = auto()
    GOTHIC_WINDOW = auto()
    ONION_DOME = auto()
    CUSTOM_MESH = auto()


@dataclass
class SceneNode:
    """A single node in the scene hierarchy.

    Each node owns a *transform*, a dict of *parameters* (type-specific),
    and an optional cached *mesh*.
    """

    name: str
    node_type: NodeType = NodeType.GROUP
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    transform: Transform = field(default_factory=Transform)
    parameters: dict[str, Any] = field(default_factory=dict)

    # Cached mesh (generated from parameters on demand)
    _mesh: MeshData | None = field(default=None, repr=False)

    # OCC shape (when OCC back-end active)
    _occ_shape: Any = field(default=None, repr=False)

    # hierarchy
    parent: SceneNode | None = field(default=None, repr=False)
    children: list[SceneNode] = field(default_factory=list, repr=False)

    # dirty flag → regenerate mesh
    _dirty: bool = True

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

    # ── repr ───────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"SceneNode(name={self.name!r}, type={self.node_type.name}, "
            f"children={len(self.children)})"
        )
