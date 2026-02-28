"""Scene manager — owns the root node and coordinates mesh generation."""

from __future__ import annotations

from archpapercraft.core_geometry.primitives import (
    MeshData,
    make_box_mesh,
    make_cone_mesh,
    make_cylinder_mesh,
)
from archpapercraft.scene_graph.node import NodeType, SceneNode


class Scene:
    """Top-level scene container."""

    def __init__(self) -> None:
        self.root = SceneNode(name="Scene", node_type=NodeType.GROUP)

    # ── node creation convenience ──────────────────────────────────────

    def add_node(
        self, name: str, node_type: NodeType, parent: SceneNode | None = None, **params
    ) -> SceneNode:
        node = SceneNode(name=name, node_type=node_type, parameters=dict(params))
        target = parent if parent is not None else self.root
        target.add_child(node)
        return node

    def remove_node(self, node: SceneNode) -> None:
        if node.parent:
            node.parent.remove_child(node)

    def find_node(self, node_id: str) -> SceneNode | None:
        return self.root.find_by_id(node_id)

    # ── mesh regeneration ──────────────────────────────────────────────

    def rebuild_meshes(self) -> None:
        """Walk the tree and regenerate meshes for dirty nodes."""
        for node in self.root.all_nodes():
            if node.is_dirty:
                self._generate_mesh(node)

    def _generate_mesh(self, node: SceneNode) -> None:
        """Generate (or regenerate) mesh from the node's type + parameters."""
        p = node.parameters

        if node.node_type == NodeType.PRIMITIVE_BOX:
            node.mesh = make_box_mesh(
                p.get("dx", 1.0), p.get("dy", 1.0), p.get("dz", 1.0)
            )

        elif node.node_type == NodeType.PRIMITIVE_CYLINDER:
            node.mesh = make_cylinder_mesh(
                p.get("radius", 0.5), p.get("height", 1.0), p.get("segments", 32)
            )

        elif node.node_type == NodeType.PRIMITIVE_CONE:
            node.mesh = make_cone_mesh(
                p.get("radius_bottom", 0.5),
                p.get("radius_top", 0.0),
                p.get("height", 1.0),
                p.get("segments", 32),
            )

        elif node.node_type in (
            NodeType.WALL,
            NodeType.OPENING,
            NodeType.ROOF,
            NodeType.GOTHIC_WINDOW,
            NodeType.ONION_DOME,
        ):
            # Delegated to arch_presets module (lazy import to avoid circular)
            from archpapercraft.arch_presets import generate_preset_mesh

            node.mesh = generate_preset_mesh(node)

        elif node.node_type == NodeType.GROUP:
            pass  # groups have no own mesh

    # ── query ──────────────────────────────────────────────────────────

    def all_mesh_nodes(self) -> list[SceneNode]:
        """Return every node that has a non-None mesh."""
        return [n for n in self.root.all_nodes() if n.mesh is not None]

    def collect_meshes(self) -> list[MeshData]:
        """Return a flat list of all meshes (for export / analysis)."""
        return [n.mesh for n in self.all_mesh_nodes()]
